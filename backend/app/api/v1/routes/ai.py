import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal, get_principal
from app.core.config import settings
from app.db.session import SessionFactory, get_session
from app.models.chat import ChatSession
from app.models.message import Message, MessageRole
from app.models.uploaded_report import UploadedReport
from app.repositories.users import get_or_create_user
from app.schemas.ai import AIChatRequest, DoctorRecommendationResponse, LanguageModeRequest, LanguageModeResponse, MedicalReportSummary, RecommendationRequest, RecommendationResponse, ReportSummaryRequest, ReportSummaryResponse
from app.services.chats import owned_chat
from app.services.gemini import require_gemini_key
from app.services.medical_qa import DISCLAIMER, detect_language, medical_qa_graph
from app.services.report_summarization import generate_report_summary, parse_stored_summary
from app.services.session_memory import merge_memory, read_memory
from app.services.recommendations import make_doctor_recommendations, make_recommendations

logger = logging.getLogger(__name__)
router = APIRouter()


async def _response_language(session: AsyncSession, chat_session: ChatSession) -> str:
    if chat_session.language_mode != "auto":
        return chat_session.language_mode
    latest = await session.scalar(select(Message).where(Message.session_id == chat_session.id, Message.role == MessageRole.USER).order_by(Message.created_at.desc()).limit(1))
    return detect_language(latest.content) if latest else "english"


def _sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n".encode("utf-8")


@router.post("/chat")
async def chat(
    payload: AIChatRequest,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Question cannot be blank")
    try:
        require_gemini_key()
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Medical Q&A is not configured") from exc

    user = await get_or_create_user(session, principal)
    chat_session = await owned_chat(session, payload.session_id, user.id)
    report_count = await session.scalar(
        select(func.count(UploadedReport.id)).where(
            UploadedReport.session_id == chat_session.id,
            UploadedReport.user_id == user.id,
        )
    )
    previous = await session.scalars(
        select(Message)
        .where(Message.session_id == chat_session.id)
        .order_by(Message.created_at.desc())
        .limit(16)
    )
    history = [
        {"role": message.role.value, "content": message.content}
        for message in reversed(previous.all())
    ]
    language_mode = chat_session.language_mode
    memory = await read_memory(session, chat_session.id, user.id)
    user_message = Message(session_id=chat_session.id, role=MessageRole.USER, content=question)
    session.add(user_message)
    chat_session.updated_at = datetime.now(timezone.utc)
    await session.commit()

    async def stream_events():
        citations: list[dict[str, Any]] = []
        answer: str | None = None
        yield _sse({"type": "started"})
        try:
            graph = medical_qa_graph()
            initial_state = {
                "user_id": user.id,
                "session_id": chat_session.id,
                "question": question,
                "history": history,
                "language_mode": language_mode,
                "memory": memory,
                "has_reports": bool(report_count),
            }
            async for mode, chunk in graph.astream(initial_state, stream_mode=["custom", "updates"]):
                if mode == "custom" and isinstance(chunk, dict):
                    if chunk.get("type") == "citations":
                        citations = chunk.get("citations", [])
                    yield _sse(chunk)
                elif mode == "updates" and isinstance(chunk, dict):
                    generated = chunk.get("generate_grounded_answer")
                    if isinstance(generated, dict) and isinstance(generated.get("answer"), str):
                        answer = generated["answer"]
            if not answer:
                raise RuntimeError("The medical Q&A workflow did not return an answer")
            async with SessionFactory() as write_session:
                stored_chat = await write_session.get(ChatSession, chat_session.id)
                if stored_chat is not None:
                    stored_chat.updated_at = datetime.now(timezone.utc)
                    write_session.add(
                        Message(
                            session_id=chat_session.id,
                            role=MessageRole.ASSISTANT,
                            content=answer,
                            citations=citations,
                        )
                    )
                    await write_session.commit()
                    report_names = list(dict.fromkeys(item["report_name"] for item in citations))
                    diagnosis_terms = list(dict.fromkeys(re.findall(r"\b(?:diabetes|hypertension|anemia|anaemia|asthma|arthritis|kidney disease|heart disease|hypothyroidism|hyperthyroidism|chronic kidney disease)\b", answer, re.I)))
                    await merge_memory(write_session, chat_session.id, user.id, {"reports": report_names, "diagnoses": diagnosis_terms, "patient_name": memory.get("patient_name"), "last_topic": question})
            yield _sse({"type": "done", "citations": citations, "disclaimer": DISCLAIMER})
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Medical Q&A failed for session %s", chat_session.id)
            yield _sse({"type": "error", "message": "I couldn't complete that report-based answer. Please try again."})

    return StreamingResponse(
        stream_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.post("/language-mode", response_model=LanguageModeResponse)
async def set_language_mode(payload: LanguageModeRequest, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> LanguageModeResponse:
    user = await get_or_create_user(session, principal)
    chat_session = await owned_chat(session, payload.session_id, user.id)
    chat_session.language_mode = payload.mode
    await session.commit()
    return LanguageModeResponse(session_id=chat_session.id, mode=chat_session.language_mode)


@router.post("/recommendations", response_model=RecommendationResponse)
async def recommendations(payload: RecommendationRequest, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> RecommendationResponse:
    try:
        require_gemini_key()
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Recommendations are not configured") from exc
    user = await get_or_create_user(session, principal)
    chat = await owned_chat(session, payload.session_id, user.id)
    try:
        mode = await _response_language(session, chat)
        return await make_recommendations(session, user.id, payload.session_id, payload.question, mode)
    except Exception as exc:
        logger.exception("Medical recommendation generation failed for session %s", payload.session_id)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Recommendations are temporarily unavailable") from exc


@router.post("/doctor-recommendation", response_model=DoctorRecommendationResponse)
async def doctor_recommendation(payload: RecommendationRequest, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> DoctorRecommendationResponse:
    user = await get_or_create_user(session, principal)
    chat = await owned_chat(session, payload.session_id, user.id)
    try:
        mode = await _response_language(session, chat)
        return await make_doctor_recommendations(session, user.id, payload.session_id, payload.question, mode)
    except Exception as exc:
        logger.exception("Doctor recommendation lookup failed for session %s", payload.session_id)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Doctor recommendations are temporarily unavailable") from exc


@router.post("/report-summary", response_model=ReportSummaryResponse)
async def create_report_summary(
    payload: ReportSummaryRequest,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> ReportSummaryResponse:
    try:
        require_gemini_key()
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Medical report summarization is not configured") from exc
    user = await get_or_create_user(session, principal)
    report = await session.scalar(
        select(UploadedReport).where(UploadedReport.id == payload.report_id, UploadedReport.user_id == user.id)
    )
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    await owned_chat(session, report.session_id, user.id)
    if report.summary_data:
        summary = parse_stored_summary(report)
    else:
        try:
            summary = await generate_report_summary(session, report)
        except ValueError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        except Exception as exc:
            logger.exception("Report summary generation failed for report %s", report.id)
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Report summary generation is temporarily unavailable") from exc
    if summary is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Stored report summary is invalid")
    return ReportSummaryResponse(
        report_id=report.id,
        report_name=report.file_name,
        generated_at=report.summary_generated_at,
        summary=summary,
    )
