from fastapi import APIRouter

from app.core.config import settings
from app.domain.schemas import ReviewMetaResponse

router = APIRouter(prefix="/api/v1/meta", tags=["meta"])


@router.get("/review", response_model=ReviewMetaResponse)
def review_meta() -> ReviewMetaResponse:
    configured_mode = "full" if settings.enable_medgemma and settings.enable_icd_model else "degraded"
    return ReviewMetaResponse(
        architecture=settings.architecture_name,
        medgemma_model=settings.llm_model,
        icd_model_name=settings.icd_model_name,
        medgemma_enabled=settings.enable_medgemma,
        icd_stage_enabled=settings.enable_icd_model,
        configured_mode=configured_mode,
        ollama_base_url=settings.ollama_base_url,
        pipeline_steps=[
            "MedGemma understanding",
            "ICD-10 prediction",
            "Rule engine validation",
            "MedGemma report generation",
        ],
        judge_talking_points=[
            "Models generate clinical knowledge and rules enforce coding correctness.",
            "MedGemma owns understanding and report generation, not just a summary stage.",
            "The ICD model owns ICD candidate prediction as a separate stage before validation.",
            "If a model stage is unavailable the response drops to degraded mode with explicit fallback notes.",
        ],
        model_download_commands=[
            "Install Ollama from https://ollama.com/download",
            f"ollama pull {settings.llm_model}",
            "pip install \"transformers>=4.40,<5.0\" \"torch>=2.2,<3.0\" \"huggingface_hub>=0.23,<1.0\"",
            f"huggingface-cli download {settings.icd_model_name} --local-dir models/icd10_prediction",
        ],
    )
