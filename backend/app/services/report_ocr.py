import asyncio
import logging
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor

import fitz
import numpy as np
from PIL import Image, ImageOps

_ocr = None
_ocr_lock = asyncio.Lock()
MAX_IMAGE_PIXELS = 40_000_000
logger = logging.getLogger(__name__)


async def extract_text(data: bytes, mime_type: str, max_pages: int, report_id: str | None = None) -> str:
    """Extract native PDF text first, OCRing scanned pages and image uploads."""
    if mime_type == "application/pdf":
        return await asyncio.to_thread(_extract_pdf, data, max_pages, report_id)
    return await asyncio.to_thread(_extract_image, data, report_id)


def _get_ocr():
    global _ocr
    if _ocr is None:
        from paddleocr import PaddleOCR

        _ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        )
    return _ocr


def warm_ocr_model() -> None:
    """Load PaddleOCR outside the first report request."""
    started = time.perf_counter()
    _get_ocr()
    logger.info("report_ocr_model_warm seconds=%.3f", time.perf_counter() - started)


def _result_lines(result) -> list[str]:
    lines: list[str] = []
    for item in result:
        payload = getattr(item, "json", None)
        if callable(payload):
            payload = payload()
        if isinstance(payload, str):
            payload = json.loads(payload)
        if isinstance(payload, dict):
            payload = payload.get("res", payload)
            texts = payload.get("rec_texts", []) if isinstance(payload, dict) else []
            boxes = payload.get("rec_boxes", []) if isinstance(payload, dict) else []
            if boxes is not None and len(boxes) == len(texts):
                ordered = sorted(zip(boxes, texts), key=lambda pair: (int(pair[0][1]), int(pair[0][0])))
                lines.extend(str(text).strip() for _, text in ordered if str(text).strip())
            else:
                lines.extend(str(text).strip() for text in texts if str(text).strip())
            continue
        # Support PaddleOCR 2.x result form if deployments pin it intentionally.
        for row in item or []:
            if isinstance(row, (list, tuple)) and len(row) > 1 and row[1]:
                lines.append(str(row[1][0]).strip())
    return lines


def _ocr_array(array: np.ndarray) -> str:
    lines = _result_lines(_get_ocr().predict(array))
    return "\n".join(lines)


def _extract_pdf(data: bytes, max_pages: int, report_id: str | None = None) -> str:
    total_started = time.perf_counter()
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        if doc.page_count > max_pages:
            raise ValueError(f"PDF exceeds the {max_pages}-page limit")
        extracted: list[str | None] = [None] * doc.page_count
        ocr_pages: list[tuple[int, np.ndarray]] = []
        for page_number, page in enumerate(doc, start=1):
            page_started = time.perf_counter()
            native = page.get_text("text", sort=True).strip()
            # OCR only pages with effectively no embedded text, preserving native layout elsewhere.
            if len("".join(native.split())) >= 20:
                extracted[page_number - 1] = f"--- Page {page_number} ---\n{native}"
                logger.info("report_page_timing report_id=%s page=%d stage=native_text seconds=%.3f", report_id, page_number, time.perf_counter() - page_started)
            else:
                page_area = max(1, page.rect.width * page.rect.height)
                max_dimension = max(page.rect.width, page.rect.height, 1)
                scale = min(2.0, (20_000_000 / page_area) ** 0.5, 8_000 / max_dimension)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
                ocr_pages.append((page_number, np.asarray(image)))
        if ocr_pages:
            def recognize(item: tuple[int, np.ndarray]) -> tuple[int, str, float]:
                page_number, image_array = item
                page_started = time.perf_counter()
                result = _ocr_array(image_array)
                elapsed = time.perf_counter() - page_started
                logger.info("report_page_timing report_id=%s page=%d stage=ocr seconds=%.3f", report_id, page_number, elapsed)
                return page_number, result, elapsed

            with ThreadPoolExecutor(max_workers=min(2, len(ocr_pages)), thread_name_prefix="report-ocr") as pool:
                for page_number, body, _ in pool.map(recognize, ocr_pages):
                    extracted[page_number - 1] = f"--- Page {page_number} ---\n{body}".rstrip()
        logger.info("report_pdf_timing report_id=%s pages=%d scanned_pages=%d seconds=%.3f", report_id, doc.page_count, len(ocr_pages), time.perf_counter() - total_started)
        return "\n\n".join(part or "" for part in extracted).strip()
    finally:
        doc.close()


def _extract_image(data: bytes, report_id: str | None = None) -> str:
    with Image.open(io.BytesIO(data)) as source:
        if source.width * source.height > MAX_IMAGE_PIXELS:
            raise ValueError("Image dimensions exceed the processing limit")
        image = ImageOps.exif_transpose(source).convert("RGB")
        started = time.perf_counter()
        result = _ocr_array(np.asarray(image)).strip()
        logger.info("report_page_timing report_id=%s page=1 stage=ocr seconds=%.3f", report_id, time.perf_counter() - started)
        return result


async def run_ocr(data: bytes, mime_type: str, max_pages: int, report_id: str | None = None) -> str:
    # Paddle model initialization and inference are CPU-heavy; serialize model calls per process.
    started = time.perf_counter()
    async with _ocr_lock:
        result = await extract_text(data, mime_type, max_pages, report_id)
    logger.info("report_ocr_timing report_id=%s mime_type=%s bytes=%d seconds=%.3f", report_id, mime_type, len(data), time.perf_counter() - started)
    return result
