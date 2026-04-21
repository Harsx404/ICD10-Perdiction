from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

def test_review_meta_includes_realigned_model_stack() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/meta/review")

    assert response.status_code == 200
    payload = response.json()
    assert payload["medgemma_model"] == settings.llm_model
    assert payload["icd_model_name"] == settings.icd_model_name
    expected_mode = "full" if settings.enable_medgemma and settings.enable_icd_model else "degraded"
    assert payload["configured_mode"] == expected_mode
    assert payload["pipeline_steps"] == [
        "MedGemma understanding",
        "ICD-10 prediction",
        "Rule engine validation",
        "MedGemma report generation",
    ]
