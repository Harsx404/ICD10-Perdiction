from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings
from app.domain.schemas import FinalClinicalContext
from app.services.documentation import DocumentationService

log = logging.getLogger(__name__)


class ClinicalReportService(ABC):
    @abstractmethod
    def generate(self, context: FinalClinicalContext) -> str:
        raise NotImplementedError


class MedGemmaClinicalReportService(ClinicalReportService):
    def generate(self, context: FinalClinicalContext) -> str:
        if not settings.enable_medgemma:
            raise RuntimeError("MedGemma report stage is disabled.")

        payload = {
            "model": settings.llm_model,
            "stream": False,
            "think": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a Clinical AI Assistant. "
                        "Generate a concise structured clinical report using only the provided findings. "
                        "Do not add unsupported diseases, risks, or ICD codes."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Use the following validated clinical context and generate a concise SOAP-style report.\n\n"
                        f"{json.dumps(context.model_dump(), indent=2)}"
                    ),
                },
            ],
        }

        response = httpx.post(
            f"{settings.ollama_base_url}/api/chat",
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        report = response.json().get("message", {}).get("content", "").strip()
        log.info("[reporting] raw_response_length=%d", len(report))
        if not report:
            raise ValueError("MedGemma report stage returned an empty response.")
        return report


class FallbackClinicalReportService(ClinicalReportService):
    def __init__(self) -> None:
        self.documentation = DocumentationService()

    def generate(self, context: FinalClinicalContext) -> str:
        return self.documentation.generate(context)

