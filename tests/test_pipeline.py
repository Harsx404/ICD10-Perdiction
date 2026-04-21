from fastapi.testclient import TestClient

from app.domain.schemas import (
    ClinicalEntities,
    ClinicalNoteRequest,
    ClinicalUnderstandingResult,
    DiagnosisSuggestion,
    IcdCode,
    IcdPredictionCandidate,
    RiskSignal,
)
from app.main import app
from app.services.icd_prediction import IcdPredictionService
from app.services.pipeline import ClinicalAnalysisPipeline
from app.services.reporting import ClinicalReportService
from app.services.rules import RuleEngineService
from app.services.understanding import ClinicalUnderstandingService


class TrackingUnderstandingService(ClinicalUnderstandingService):
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def analyze(self, text: str, *, images: list[str] | None = None) -> ClinicalUnderstandingResult:
        self.calls.append("understanding")
        return ClinicalUnderstandingResult(
            entities=ClinicalEntities(diseases=["hypertension"]),
            diagnosis=[
                DiagnosisSuggestion(
                    label="Hypertension",
                    probability=0.91,
                    rationale="Tracked test diagnosis.",
                )
            ],
            risks=[],
        )


class TrackingIcdPredictionService(IcdPredictionService):
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def predict(
        self,
        text: str,
        understanding: ClinicalUnderstandingResult,
    ) -> list[IcdPredictionCandidate]:
        del text, understanding
        self.calls.append("icd")
        return [
            IcdPredictionCandidate(
                code="I10",
                description="Essential (primary) hypertension",
                confidence=0.93,
                evidence=["hypertension"],
            )
        ]


class TrackingRuleEngine(RuleEngineService):
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def validate(
        self,
        understanding: ClinicalUnderstandingResult,
        candidates: list[IcdPredictionCandidate],
    ) -> tuple[list[IcdCode], list[str]]:
        del understanding, candidates
        self.calls.append("rules")
        return [
            IcdCode(
                code="I10",
                description="Essential (primary) hypertension",
                confidence=0.93,
            )
        ], []


class TrackingReportService(ClinicalReportService):
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def generate(self, context) -> str:
        del context
        self.calls.append("report")
        return "Structured report"


class BrokenUnderstandingService(ClinicalUnderstandingService):
    def analyze(self, text: str, *, images: list[str] | None = None) -> ClinicalUnderstandingResult:
        del text
        raise RuntimeError("MedGemma unavailable")


class BrokenIcdPredictionService(IcdPredictionService):
    def predict(
        self,
        text: str,
        understanding: ClinicalUnderstandingResult,
    ) -> list[IcdPredictionCandidate]:
        del text, understanding
        raise RuntimeError("BioBERT unavailable")


def test_pipeline_order_full_mode() -> None:
    calls: list[str] = []
    pipeline = ClinicalAnalysisPipeline(
        understanding_service=TrackingUnderstandingService(calls),
        fallback_understanding_service=TrackingUnderstandingService([]),
        icd_prediction_service=TrackingIcdPredictionService(calls),
        fallback_icd_prediction_service=TrackingIcdPredictionService([]),
        rule_engine=TrackingRuleEngine(calls),
        report_service=TrackingReportService(calls),
        fallback_report_service=TrackingReportService([]),
    )

    response = pipeline.run(ClinicalNoteRequest(note_text="Patient has hypertension."))

    assert response.mode == "full"
    assert calls == ["understanding", "icd", "rules", "report"]


def test_api_returns_prompt_aligned_schema() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/analyze",
        json={"note_text": "Patient has hypertension. Denies chest pain."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] in {"full", "degraded"}
    assert set(payload["entities"]) == {
        "diseases",
        "symptoms",
        "severity",
        "negations",
        "complications",
    }
    assert "llm_summary" not in payload


def test_negated_findings_are_excluded_from_icd_output() -> None:
    payload = ClinicalNoteRequest(
        note_text="Patient has hypertension and type 2 diabetes mellitus. Denies chest pain."
    )

    response = ClinicalAnalysisPipeline().run(payload)
    returned_codes = {item.code for item in response.icd_codes}

    assert "I10" in returned_codes
    assert "E11.9" in returned_codes
    assert "R07.9" not in returned_codes
    assert "chest pain" in response.entities.negations


def test_combination_rule_applies_for_diabetes_with_nephropathy() -> None:
    payload = ClinicalNoteRequest(
        note_text="Patient has uncontrolled diabetes with kidney damage."
    )

    response = ClinicalAnalysisPipeline().run(payload)
    returned_codes = {item.code for item in response.icd_codes}

    assert response.mode in {"full", "degraded"}
    assert "uncontrolled" in response.entities.severity
    assert "nephropathy" in response.entities.complications
    assert "E11.21" in returned_codes
    assert "E11.9" not in returned_codes


def test_degraded_mode_when_medgemma_stage_fails() -> None:
    pipeline = ClinicalAnalysisPipeline(
        understanding_service=BrokenUnderstandingService(),
        report_service=TrackingReportService([]),
        fallback_report_service=TrackingReportService([]),
    )

    response = pipeline.run(ClinicalNoteRequest(note_text="Patient has hypertension."))

    assert response.mode == "degraded"
    assert any("MedGemma understanding stage fallback activated" in note for note in response.validation_notes)


def test_degraded_mode_when_icd_stage_fails() -> None:
    pipeline = ClinicalAnalysisPipeline(
        understanding_service=TrackingUnderstandingService([]),
        fallback_understanding_service=TrackingUnderstandingService([]),
        icd_prediction_service=BrokenIcdPredictionService(),
        fallback_icd_prediction_service=TrackingIcdPredictionService([]),
        report_service=TrackingReportService([]),
        fallback_report_service=TrackingReportService([]),
    )

    response = pipeline.run(ClinicalNoteRequest(note_text="Patient has hypertension."))

    assert response.mode == "degraded"
    assert any("BioBERT ICD stage fallback activated" in note for note in response.validation_notes)
    assert response.icd_codes[0].code == "I10"
