from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class MedicalSourceCreate(BaseModel):
    source_key: str = Field(min_length=2, max_length=120, pattern=r"^[a-zA-Z0-9._:-]+$")
    title: str = Field(min_length=3, max_length=500)
    organization: str = Field(min_length=2, max_length=240)
    source_url: AnyHttpUrl
    source_type: str = Field(min_length=2, max_length=80)
    medical_category: Literal[
        "condition", "symptoms", "laboratory_test", "medicine", "procedure",
        "preventive_healthcare", "nutrition", "pregnancy_maternal_health",
        "child_adolescent_health", "elderly_healthcare", "emergency_first_aid",
        "medical_terminology", "specialist_department", "patient_education",
    ] = "patient_education"
    specialty: str | None = Field(default=None, max_length=120)
    specialties: list[str] = Field(default_factory=list, max_length=10)
    relevant_topic: str = Field(min_length=2, max_length=240)
    jurisdiction: str | None = Field(default=None, max_length=120)
    publication_date: str | None = Field(default=None, max_length=40)
    last_updated_date: str | None = Field(default=None, max_length=40)
    review_date: datetime | None = None
    source_version: str | None = Field(default=None, max_length=120)
    license_permission: str = Field(min_length=4, max_length=500)
    language: str = Field(default="en", min_length=2, max_length=30)


class MedicalSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_key: str
    title: str
    organization: str
    source_url: str
    source_type: str
    medical_category: str
    specialty: str | None
    specialties: list[str]
    relevant_topic: str
    jurisdiction: str | None
    publication_date: str | None
    last_updated_date: str | None
    date_retrieved: datetime
    review_date: datetime | None
    source_version: str | None
    license_permission: str
    language: str
    review_status: str
    reviewer_clerk_id: str | None
    created_at: datetime


class ReviewRequest(BaseModel):
    action: Literal["approve", "reject", "retire"]
    notes: str | None = Field(default=None, max_length=4_000)


class MedicalKnowledgeDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    title: str
    created_at: datetime


class MedicalKnowledgeVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID | None = None
    document_id: UUID
    version_label: str
    original_file_name: str
    mime_type: str
    file_size: int
    content_sha256: str
    processing_status: str
    approval_status: str
    is_active: bool
    processing_error: str | None
    reviewed_by_clerk_id: str | None
    reviewed_at: datetime | None
    created_at: datetime


class MedicalKnowledgeVersionDetailRead(MedicalKnowledgeVersionRead):
    extracted_text: str | None = None
    source_status: str
    source_title: str
    source_url: str
    medical_category: str
    organization: str
    relevant_topic: str
    specialty: str | None = None
    specialties: list[str]
    jurisdiction: str | None = None
    language: str
    license_permission: str


class KnowledgeIngestionJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version_id: UUID
    operation: str
    status: str
    attempts: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class MedicalKnowledgeCitation(BaseModel):
    source_type: Literal["medical_knowledge"] = "medical_knowledge"
    source_id: UUID
    document_id: UUID
    version_id: UUID
    title: str
    organization: str
    source_url: str
    section: str
    page: int | None = None
    publication_date: str | None = None
    last_updated_date: str | None = None
    version: str
    jurisdiction: str | None = None
    language: str
    excerpt: str
