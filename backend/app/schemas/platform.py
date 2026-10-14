from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class VoiceTranscriptionResponse(BaseModel):
    session_id: UUID
    text: str
    language: str | None = None
    language_probability: float | None = None


class HospitalRecommendationRequest(BaseModel):
    session_id: UUID
    city: str = Field(min_length=2, max_length=120)
    region: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=240)
    condition: str | None = Field(default=None, max_length=500)


class HospitalResult(BaseModel):
    id: UUID
    name: str
    city: str
    specialization: str
    address: str
    phone: str | None
    website: str | None
    rating: float | None
    reason: str


class HospitalRecommendationResponse(BaseModel):
    hospitals: list[HospitalResult]
    specialties: list[str]
    disclaimer: str


class EmailShareRequest(BaseModel):
    session_id: UUID
    recipient_email: EmailStr
    include_report_summaries: bool = True


class EmailShareResponse(BaseModel):
    message: str


class HospitalImportRow(BaseModel):
    name: str = Field(min_length=2, max_length=240)
    city: str = Field(min_length=2, max_length=120)
    specialization: str = Field(min_length=2, max_length=120)
    address: str = Field(min_length=2)
    phone: str | None = None
    website: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
