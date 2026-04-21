from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ClinicalNoteRequest(BaseModel):
    patient_id: str | None = None
    encounter_id: str | None = None
    note_text: str = Field(default="", description="Free-text clinical note")
    images: list[str] = Field(default_factory=list, description="Base64-encoded images for vision model")
    include_report: bool = True

    @model_validator(mode="after")
    def _require_note_or_images(self) -> "ClinicalNoteRequest":
        if not self.note_text.strip() and not self.images:
            raise ValueError("Either note_text or at least one image must be provided.")
        return self


class ClinicalEntities(BaseModel):
    diseases: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    severity: list[str] = Field(default_factory=list)
    negations: list[str] = Field(default_factory=list)
    complications: list[str] = Field(default_factory=list)


class ExtractedEntity(BaseModel):
    label: str
    entity_type: Literal["disease", "symptom", "severity", "complication"]
    mention: str
    negated: bool = False
    confidence: float = Field(..., ge=0.0, le=1.0)
    start: int | None = None
    end: int | None = None


class IcdPredictionCandidate(BaseModel):
    code: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)


class IcdCode(BaseModel):
    code: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class DiagnosisSuggestion(BaseModel):
    label: str
    probability: float = Field(..., ge=0.0, le=1.0)
    rationale: str


class RiskSignal(BaseModel):
    label: str
    severity: Literal["low", "moderate", "high"]
    rationale: str


class ClinicalUnderstandingResult(BaseModel):
    entities: ClinicalEntities
    diagnosis: list[DiagnosisSuggestion] = Field(default_factory=list)
    risks: list[RiskSignal] = Field(default_factory=list)
    mentions: list[ExtractedEntity] = Field(default_factory=list)
    preliminary_report: str = ""


class FinalClinicalContext(BaseModel):
    note_text: str
    mode: Literal["full", "degraded"]
    entities: ClinicalEntities
    icd_codes: list[IcdCode] = Field(default_factory=list)
    diagnosis: list[DiagnosisSuggestion] = Field(default_factory=list)
    risks: list[RiskSignal] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)


class PrimaryIcdCode(BaseModel):
    code: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str = ""


class ClinicalAnalysisResponse(BaseModel):
    mode: Literal["full", "degraded"]
    entities: ClinicalEntities
    icd_codes: list[IcdCode]
    primary_icd_code: PrimaryIcdCode | None = None
    diagnosis: list[DiagnosisSuggestion]
    risks: list[RiskSignal]
    report: str
    validation_notes: list[str] = Field(default_factory=list)
    doc_id: str | None = None          # MongoDB document id, set after persistence


class ReviewMetaResponse(BaseModel):
    architecture: str
    medgemma_model: str
    icd_model_name: str
    medgemma_enabled: bool
    icd_stage_enabled: bool
    configured_mode: Literal["full", "degraded"]
    ollama_base_url: str
    pipeline_steps: list[str]
    judge_talking_points: list[str]
    model_download_commands: list[str]
