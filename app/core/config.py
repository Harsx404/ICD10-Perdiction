from dataclasses import dataclass
import os
from pathlib import Path


def _load_repo_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            os.environ.setdefault(key, value)


def _as_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


_load_repo_env()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Clinical Intelligence System")
    app_version: str = "0.3.0"
    architecture_name: str = "modular-monolith"
    llm_model: str = os.getenv("LLM_MODEL", "MedAIBase/MedGemma1.5:4b")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    icd_model_name: str = os.getenv("ICD_MODEL_NAME", "AkshatSurolia/ICD-10-Code-Prediction")
    biogpt_model_name: str = os.getenv("BIOGPT_MODEL_NAME", "microsoft/biogpt")
    enable_medgemma: bool = _as_bool("ENABLE_MEDGEMMA", False)
    enable_icd_model: bool = _as_bool("ENABLE_ICD_MODEL", False)
    enable_biogpt: bool = _as_bool("ENABLE_BIOGPT", False)
    icd_top_k: int = int(os.getenv("ICD_TOP_K", "5"))
    # FAISS vector retriever
    icd_index_path: str = os.getenv("ICD_INDEX_PATH", "models/icd_index")
    icd_retriever_model: str = os.getenv("ICD_RETRIEVER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    icd_retrieval_k: int = int(os.getenv("ICD_RETRIEVAL_K", "100"))
    # MongoDB persistence
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME", "clinical_intelligence")
    # MongoDB persistence
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME", "clinical_intelligence")


settings = Settings()
