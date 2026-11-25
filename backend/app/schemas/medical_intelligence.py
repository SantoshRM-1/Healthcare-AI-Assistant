from pydantic import BaseModel, ConfigDict, Field


class LabFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_name: str
    original_name: str
    category: str
    value: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    status: str = Field(
        description="low, normal, high, ambiguous, unreadable, missing, or unassessed"
    )
    specialty: str | None = None
    page: int | None = None
    source_location: str
    original_text: str
    critical_status: str = "not_assessed_no_configured_rules"


class LabAnalysis(BaseModel):
    findings: list[LabFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PrescriptionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medicine_name_as_written: str | None = None
    generic_name: str | None = None
    strength: str | None = None
    dosage_instructions_as_written: str | None = None
    route_as_written: str | None = None
    frequency_as_written: str | None = None
    timing_as_written: str | None = None
    duration_as_written: str | None = None
    food_instructions_as_written: str | None = None
    prescriber_as_written: str | None = None
    prescription_date_as_written: str | None = None
    page: int | None = None
    source_location: str
    original_text: str
    extraction_status: str = "requires_confirmation"


class PrescriptionAnalysis(BaseModel):
    items: list[PrescriptionItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SymptomMention(BaseModel):
    concept: str
    phrase_as_reported: str
    status: str = "patient_reported_not_diagnosis"
    duration_as_reported: str | None = None


class SymptomAnalysis(BaseModel):
    symptoms: list[SymptomMention] = Field(default_factory=list)
    condition_mentions: list[dict[str, str]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ClinicalIntelligenceContext(BaseModel):
    laboratory: LabAnalysis = Field(default_factory=LabAnalysis)
    prescription: PrescriptionAnalysis = Field(default_factory=PrescriptionAnalysis)
    patient_reported: SymptomAnalysis = Field(default_factory=SymptomAnalysis)
