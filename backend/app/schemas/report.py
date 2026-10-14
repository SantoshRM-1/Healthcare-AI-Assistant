from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    session_id: UUID
    file_name: str
    file_type: str
    file_size: int
    file_url: str
    processing_status: str
    processing_stage: str
    upload_date: datetime


class ReportRead(ReportSummary):
    raw_extracted_text: str | None


class ReportProcessingDebug(BaseModel):
    report_id: UUID
    status: str
    stage: str
    error: str | None
    created_at: datetime
    updated_at: datetime
    cloudinary_uploaded: bool
    text_extracted: bool
    chunks_created: int
    embeddings_created: int
    vectors_saved: int
