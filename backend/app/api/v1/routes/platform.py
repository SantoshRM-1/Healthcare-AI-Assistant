import asyncio
import logging
import time
from pathlib import Path
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal, get_principal
from app.core.config import settings
from app.db.session import get_session
from app.models.chat import ChatSession
from app.models.message import Message
from app.models.session_memory import RecommendationRecord
from app.models.uploaded_report import UploadedReport
from app.repositories.users import get_or_create_user
from app.schemas.platform import EmailShareRequest, EmailShareResponse, HospitalRecommendationRequest, HospitalRecommendationResponse, VoiceTranscriptionResponse
from app.services.chat_export import create_pdf, plain_text, safe_filename
from app.services.chats import owned_chat
from app.services.email_sharing import send_chat_email
from app.services.hospital_recommendations import recommend_hospitals
from app.services.voice_transcription import transcribe_audio

logger = logging.getLogger(__name__)
ai_router = APIRouter()
share_router = APIRouter()
export_router = APIRouter()


@ai_router.post("/voice", response_model=VoiceTranscriptionResponse)
async def voice_transcription(
    session_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> VoiceTranscriptionResponse:
    user = await get_or_create_user(session, principal)
    await owned_chat(session, session_id, user.id)
    suffix = Path(file.filename or "audio.webm").suffix.lower()
    if suffix not in {".webm", ".wav", ".mp3", ".m4a", ".mp4", ".ogg", ".mpeg", ".mpga", ".flac"}:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Use a supported audio recording format")
    limit = settings.voice_max_size_mb * 1024 * 1024
    data = await file.read(limit + 1)
    await file.close()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The recording is empty")
    if len(data) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Recording exceeds {settings.voice_max_size_mb} MB")
    transcription_started = time.perf_counter()
    logger.info("voice_request stage=transcribing session_id=%s bytes=%d", session_id, len(data))
    try:
        text, language, probability = await asyncio.to_thread(transcribe_audio, data, suffix)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except Exception as exc:
        logger.exception("Voice transcription failed for chat %s", session_id)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Speech transcription is temporarily unavailable") from exc
    logger.info("voice_request_timing session_id=%s stage=total seconds=%.3f", session_id, time.perf_counter() - transcription_started)
    return VoiceTranscriptionResponse(session_id=session_id, text=text, language=language, language_probability=probability)


@ai_router.post("/hospital-recommendation", response_model=HospitalRecommendationResponse)
async def hospital_recommendation(payload: HospitalRecommendationRequest, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> HospitalRecommendationResponse:
    user = await get_or_create_user(session, principal)
    chat = await owned_chat(session, payload.session_id, user.id)
    try:
        return await recommend_hospitals(session, user.id, payload)
    except Exception as exc:
        logger.exception("Hospital lookup failed for chat %s", chat.id)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Hospital search is temporarily unavailable") from exc


@share_router.post("/email", response_model=EmailShareResponse)
async def share_chat_email(payload: EmailShareRequest, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> EmailShareResponse:
    user = await get_or_create_user(session, principal)
    chat = await owned_chat(session, payload.session_id, user.id)
    try:
        await send_chat_email(session, chat, str(payload.recipient_email), payload.include_report_summaries)
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Email sharing is not configured") from exc
    except httpx.HTTPError as exc:
        logger.exception("Resend failed for chat %s", chat.id)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "The email could not be sent right now") from exc
    return EmailShareResponse(message="Chat summary sent")


async def _export_data(chat_id: UUID, principal: Principal, session: AsyncSession):
    user = await get_or_create_user(session, principal)
    chat = await owned_chat(session, chat_id, user.id)
    messages = await session.scalars(select(Message).where(Message.session_id == chat.id).order_by(Message.created_at.asc()))
    reports = await session.scalars(select(UploadedReport).where(UploadedReport.session_id == chat.id, UploadedReport.user_id == user.id).order_by(UploadedReport.upload_date.asc()))
    recommendations = await session.scalars(select(RecommendationRecord).where(RecommendationRecord.session_id == chat.id, RecommendationRecord.user_id == user.id).order_by(RecommendationRecord.created_at.asc()))
    return chat, messages.all(), reports.all(), recommendations.all()


@export_router.get("/txt/{chat_id}")
async def export_txt(chat_id: UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> Response:
    chat, messages, reports, recommendations = await _export_data(chat_id, principal, session)
    content = plain_text(chat, messages, reports, recommendations).encode("utf-8")
    return Response(content=content, media_type="text/plain; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{safe_filename(chat.title, "txt")}"', "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@export_router.get("/pdf/{chat_id}")
async def export_pdf(chat_id: UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> Response:
    chat, messages, reports, recommendations = await _export_data(chat_id, principal, session)
    try:
        content = await asyncio.to_thread(create_pdf, chat, messages, reports, recommendations)
    except Exception as exc:
        logger.exception("PDF export failed for chat %s", chat.id)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "PDF export is temporarily unavailable") from exc
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{safe_filename(chat.title, "pdf")}"', "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
