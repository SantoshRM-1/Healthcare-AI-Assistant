from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Citation(BaseModel):
    report_id: UUID
    report_name: str
    section: str
    page: int | None = None
    excerpt: str


class AIChatRequest(BaseModel):
    session_id: UUID
    question: str = Field(min_length=1, max_length=8_000)


class LanguageModeRequest(BaseModel):
    session_id: UUID
    mode: str = Field(pattern="^(auto|english|kannada|bilingual)$")


class LanguageModeResponse(BaseModel):
    session_id: UUID
    mode: str


class RecommendationRequest(BaseModel):
    session_id: UUID
    question: str = Field(min_length=3, max_length=2_000)


class RecommendationItem(BaseModel):
    title: str
    detail: str
    category: str = "general"


class RecommendationResponse(BaseModel):
    session_id: UUID
    recommendations: list[RecommendationItem]
    sources: list["Citation"]
    disclaimer: str


class DoctorRecommendationResponse(BaseModel):
    session_id: UUID
    specialists: list[RecommendationItem]
    sources: list["Citation"]
    disclaimer: str


class SessionMemoryResponse(BaseModel):
    session_id: UUID
    language_mode: str
    memory: dict


class ReportSummaryRequest(BaseModel):
    report_id: UUID


class PatientInformation(BaseModel):
    name: str | None = None
    age: str | None = None
    date_of_birth: str | None = None
    sex: str | None = None
    other: list[str] = Field(default_factory=list)


class MedicineItem(BaseModel):
    name: str
    dosage: str | None = None
    frequency: str | None = None
    route: str | None = None
    notes: str | None = None


class MedicalReportSummary(BaseModel):
    patient_information: PatientInformation
    diagnosis: list[str] = Field(default_factory=list)
    medicines: list[MedicineItem] = Field(default_factory=list)
    important_findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ReportSummaryResponse(BaseModel):
    report_id: UUID
    report_name: str
    generated_at: datetime | None
    summary: MedicalReportSummary
