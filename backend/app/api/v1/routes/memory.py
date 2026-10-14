from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal, get_principal
from app.db.session import get_session
from app.models.chat import ChatSession
from app.models.session_memory import RecommendationRecord
from app.models.uploaded_report import UploadedReport
from app.repositories.users import get_or_create_user
from app.schemas.ai import SessionMemoryResponse
from app.services.chats import owned_chat
from app.services.session_memory import read_memory

router = APIRouter()


@router.get("/session/{session_id}", response_model=SessionMemoryResponse)
async def get_session_memory(session_id: UUID, principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)) -> SessionMemoryResponse:
    user = await get_or_create_user(session, principal)
    chat = await owned_chat(session, session_id, user.id)
    memory = await read_memory(session, chat.id, user.id)
    reports = await session.scalars(select(UploadedReport).where(UploadedReport.user_id == user.id, UploadedReport.session_id == chat.id).order_by(UploadedReport.upload_date))
    names = list(memory.get("reports", []))
    diagnoses = list(memory.get("diagnoses", []))
    for report in reports.all():
        if report.file_name not in names:
            names.append(report.file_name)
        summary = report.summary_data or {}
        info = summary.get("patient_information", {})
        if info.get("name") and not memory.get("patient_name"):
            memory["patient_name"] = info["name"]
        for diagnosis in summary.get("diagnosis", []):
            if diagnosis not in diagnoses:
                diagnoses.append(diagnosis)
    history = await session.scalars(select(RecommendationRecord).where(RecommendationRecord.user_id == user.id, RecommendationRecord.session_id == chat.id).order_by(RecommendationRecord.created_at.desc()).limit(20))
    recommendations = list(memory.get("recommendations", []))
    doctors = list(memory.get("doctor_suggestions", []))
    for record in reversed(history.all()):
        values = record.payload.get("recommendations" if record.kind == "medical" else "specialists", [])
        target = recommendations if record.kind == "medical" else doctors
        for value in values:
            title = value.get("title")
            if title and title not in target:
                target.append(title)
    memory.update({"reports": names[-30:], "diagnoses": diagnoses[-30:], "recommendations": recommendations[-30:], "doctor_suggestions": doctors[-30:]})
    return SessionMemoryResponse(session_id=chat.id, language_mode=chat.language_mode, memory=memory)
