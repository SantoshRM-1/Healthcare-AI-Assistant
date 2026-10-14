import asyncio
import logging
import time
import uuid
from functools import lru_cache
from typing import Any, Awaitable, Callable

import chromadb
import numpy as np
from google.genai import types

from app.core.config import settings
from app.services.gemini import gemini_async_client
from app.services.report_chunking import chunk_report

COLLECTION_NAME = "medassist_report_chunks_v1"
logger = logging.getLogger(__name__)


@lru_cache
def chroma_client():
    if settings.chroma_http_host:
        headers = {"Authorization": f"Bearer {settings.chroma_api_token}"} if settings.chroma_api_token else None
        return chromadb.HttpClient(host=settings.chroma_http_host, port=settings.chroma_http_port, ssl=settings.chroma_ssl, headers=headers)
    return chromadb.PersistentClient(path=settings.chroma_persist_directory)


@lru_cache
def collection():
    return chroma_client().get_or_create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


async def _embed(texts: list[str], task_type: str, title: str | None = None) -> list[list[float]]:
    if not texts:
        return []
    client = gemini_async_client()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), 32):
        batch = texts[start : start + 32]
        response = await client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type=task_type,
                title=title if task_type == "RETRIEVAL_DOCUMENT" else None,
                output_dimensionality=settings.gemini_embedding_dimensions,
            ),
        )
        for embedding in response.embeddings or []:
            if not embedding.values:
                raise RuntimeError("Gemini returned an empty report embedding")
            values = np.asarray(embedding.values, dtype=np.float32)
            norm = float(np.linalg.norm(values))
            if not norm:
                raise RuntimeError("Gemini returned an empty report embedding")
            vectors.append((values / norm).astype(float).tolist())
    if len(vectors) != len(texts):
        raise RuntimeError("Gemini returned an incomplete embedding batch")
    return vectors


async def index_report(
    report_id: uuid.UUID,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    report_name: str,
    text: str,
    progress: Callable[[str, int], Awaitable[None]] | None = None,
) -> int:
    started = time.perf_counter()
    logger.info("REPORT CHUNKING STARTED report_id=%s", report_id)
    chunks = chunk_report(text, report_name)
    if not chunks:
        raise ValueError("No text was extracted from this report")
    logger.info("REPORT CHUNKING COMPLETED report_id=%s chunks=%d seconds=%.3f", report_id, len(chunks), time.perf_counter() - started)
    if progress:
        await progress("chunks_created", len(chunks))
    embed_started = time.perf_counter()
    logger.info("REPORT EMBEDDING STARTED report_id=%s chunks=%d", report_id, len(chunks))
    embeddings = await _embed([chunk.text for chunk in chunks], "RETRIEVAL_DOCUMENT", title=report_name)
    logger.info("REPORT EMBEDDING COMPLETED report_id=%s embeddings=%d seconds=%.3f", report_id, len(embeddings), time.perf_counter() - embed_started)
    if progress:
        await progress("embeddings_created", len(embeddings))
    logger.info("report_timing report_id=%s stage=embeddings chunks=%d seconds=%.3f", report_id, len(chunks), time.perf_counter() - embed_started)
    target = collection()
    ids = [f"{report_id}:{chunk.index}" for chunk in chunks]
    metadatas = [
        {
            "report_id": str(report_id),
            "user_id": str(user_id),
            "session_id": str(session_id),
            "report_name": report_name,
            "section": chunk.section,
            "page": chunk.page if chunk.page is not None else 0,
            "chunk_index": chunk.index,
        }
        for chunk in chunks
    ]
    chroma_started = time.perf_counter()
    logger.info("REPORT VECTOR STORE STARTED report_id=%s vectors=%d", report_id, len(ids))
    if progress:
        await progress("storing_vectors", 0)
    await asyncio.to_thread(target.delete, where={"report_id": str(report_id)})
    await asyncio.to_thread(target.upsert, ids=ids, embeddings=embeddings, documents=[chunk.text for chunk in chunks], metadatas=metadatas)
    logger.info("report_timing report_id=%s stage=chroma_insert vectors=%d seconds=%.3f", report_id, len(ids), time.perf_counter() - chroma_started)
    logger.info("REPORT VECTOR STORE COMPLETED report_id=%s vectors=%d", report_id, len(ids))
    if progress:
        await progress("vectors_saved", len(ids))
    logger.info("report_timing report_id=%s stage=index_total seconds=%.3f", report_id, time.perf_counter() - started)
    return len(chunks)


async def delete_report_vectors(report_id: uuid.UUID) -> None:
    await asyncio.to_thread(collection().delete, where={"report_id": str(report_id)})


async def retrieve_chunks(user_id: uuid.UUID, session_id: uuid.UUID, question: str) -> list[dict[str, Any]]:
    query_vector = (await _embed([question], "QUESTION_ANSWERING"))[0]
    where = {"$and": [{"user_id": str(user_id)}, {"session_id": str(session_id)}]}
    found = await asyncio.to_thread(
        collection().query,
        query_embeddings=[query_vector],
        n_results=settings.rag_top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    ids = (found.get("ids") or [[]])[0]
    documents = (found.get("documents") or [[]])[0]
    metadatas = (found.get("metadatas") or [[]])[0]
    distances = (found.get("distances") or [[]])[0]
    results = []
    for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
        if distance is None or float(distance) > settings.rag_max_cosine_distance:
            continue
        results.append({"id": chunk_id, "text": document, "metadata": metadata, "distance": float(distance)})
    return results


def make_citations(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for document in documents:
        meta = document["metadata"]
        excerpt = " ".join(document["text"].split())
        citations.append(
            {
                "report_id": meta["report_id"],
                "report_name": meta["report_name"],
                "section": meta["section"],
                "page": int(meta.get("page", 0)) or None,
                "excerpt": excerpt[-900:],
            }
        )
    return citations
