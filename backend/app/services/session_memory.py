import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session_memory import RecommendationRecord, SessionMemory
from app.models.uploaded_report import UploadedReport

MEMORY_LISTS = ("reports", "diagnoses", "recommendations", "doctor_suggestions")


async def read_memory(session: AsyncSession, session_id: UUID, user_id: UUID) -> dict:
    record = await session.scalar(select(SessionMemory).where(SessionMemory.session_id == session_id, SessionMemory.user_id == user_id))
    data = dict(record.data) if record else {"patient_name": None, **{key: [] for key in MEMORY_LISTS}}
    for key in MEMORY_LISTS:
        data.setdefault(key, [])
    reports = await session.scalars(select(UploadedReport).where(UploadedReport.session_id == session_id, UploadedReport.user_id == user_id).order_by(UploadedReport.upload_date))
    for report in reports.all():
        if report.file_name not in data["reports"]:
            data["reports"].append(report.file_name)
        summary = report.summary_data or {}
        patient = summary.get("patient_information", {})
        if patient.get("name") and not data.get("patient_name"):
            data["patient_name"] = patient["name"]
        if not data.get("patient_name") and report.raw_extracted_text:
            match = re.search(r"(?im)^\s*(?:patient\s+name|patient|name)\s*[:\-]\s*([A-Za-z][A-Za-z .'-]{1,79})\s*$", report.raw_extracted_text)
            if match:
                data["patient_name"] = match.group(1).strip()
        for diagnosis in summary.get("diagnosis", []):
            if diagnosis not in data["diagnoses"]:
                data["diagnoses"].append(diagnosis)
    records = await session.scalars(select(RecommendationRecord).where(RecommendationRecord.session_id == session_id, RecommendationRecord.user_id == user_id).order_by(RecommendationRecord.created_at).limit(30))
    for item in records.all():
        key = "recommendations" if item.kind == "medical" else "doctor_suggestions"
        result_key = "recommendations" if item.kind == "medical" else "specialists"
        for value in item.payload.get(result_key, []):
            name = value.get("title")
            if name and name not in data[key]:
                data[key].append(name)
    return data


async def merge_memory(session: AsyncSession, session_id: UUID, user_id: UUID, updates: dict) -> dict:
    record = await session.scalar(select(SessionMemory).where(SessionMemory.session_id == session_id, SessionMemory.user_id == user_id))
    if record is None:
        record = SessionMemory(session_id=session_id, user_id=user_id, data={"patient_name": None, **{key: [] for key in MEMORY_LISTS}})
        session.add(record)
    data = dict(record.data or {})
    for key, value in updates.items():
        if key in MEMORY_LISTS:
            existing = list(data.get(key, []))
            for item in value if isinstance(value, list) else [value]:
                if item and item not in existing:
                    existing.append(item)
            data[key] = existing[-30:]
        elif value and key == "patient_name":
            data[key] = value
        elif value and key == "last_topic":
            data[key] = value[:500]
    record.data = data
    record.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return data
