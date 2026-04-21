from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)
from app.domain.schemas import (
    ClinicalEntities,
    ClinicalUnderstandingResult,
    DiagnosisSuggestion,
    RiskSignal,
)
from app.services.catalog import normalize_entity_label
from app.services.diagnosis import DiagnosisService
from app.services.extractor import ClinicalNlpService
from app.services.risks import RiskDetectionService


class ClinicalUnderstandingService(ABC):
    @abstractmethod
    def analyze(self, text: str, *, images: list[str] | None = None) -> ClinicalUnderstandingResult:
        raise NotImplementedError


class MedGemmaClinicalUnderstandingService(ClinicalUnderstandingService):
    def analyze(self, text: str, *, images: list[str] | None = None) -> ClinicalUnderstandingResult:
        if not settings.enable_medgemma:
            raise RuntimeError("MedGemma understanding stage is disabled.")

        payload = {
            "model": settings.llm_model,
            "stream": False,
            "think": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a Clinical AI Assistant. "
                        "Extract diseases, symptoms, severity, negations, and complications. "
                        "Suggest diagnosis and detect risks using only the note. "
                        "Also write a concise SOAP-style clinical report narrative based on the extracted findings. "
                        "Do not generate ICD codes. Return JSON only. Do not explain your reasoning.\n\n"
                        "IMPORTANT diagnosis labelling rules:\n"
                        "- Do NOT label a diagnosis as 'exacerbation' or 'with exacerbation' unless the note "
                        "explicitly documents acute worsening, ER/urgent visit, rescue inhaler use, or the "
                        "clinician explicitly writes 'exacerbation' or 'acute attack'.\n"
                        "- Chronic or recurring symptoms alone (wheezing, SOB, chest tightness) without "
                        "documented acute deterioration should be labelled as the base disease only "
                        "(e.g. 'Asthma', not 'Asthma exacerbation').\n"
                        "- Use 'probability' to reflect diagnostic certainty: documented history = 0.9+, "
                        "strongly implied = 0.7-0.89, possible/risk only = 0.3-0.69."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Analyze the following clinical note and return JSON with the exact shape "
                        "{\"entities\":{\"diseases\":[],\"symptoms\":[],\"severity\":[],\"negations\":[],\"complications\":[]},"
                        "\"diagnosis\":[{\"label\":\"\",\"probability\":0.0,\"rationale\":\"\"}],"
                        "\"risks\":[{\"label\":\"\",\"severity\":\"low|moderate|high\",\"rationale\":\"\"}],"
                        "\"report\":\"Subjective: ... Objective: ... Assessment: ... Plan: ...\"}\n\n"
                        f"Clinical note:\n{text}"
                    ),
                    **({"images": images} if images else {}),
                },
            ],
        }

        response = httpx.post(
            f"{settings.ollama_base_url}/api/chat",
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        content = response.json().get("message", {}).get("content", "")
        log.info("[understanding] raw_response_length=%d content_preview=%.120r", len(content), content)
        data = self._extract_json(content)

        entities = ClinicalEntities(
            diseases=self._normalize_list(data.get("entities", {}).get("diseases", []), restrict_types=("disease", "complication")),
            symptoms=self._normalize_list(data.get("entities", {}).get("symptoms", []), restrict_types=("symptom",)),
            severity=self._normalize_list(data.get("entities", {}).get("severity", []), restrict_types=("severity",)),
            negations=self._normalize_list(data.get("entities", {}).get("negations", [])),
            complications=self._normalize_list(data.get("entities", {}).get("complications", []), restrict_types=("complication", "disease")),
        )
        diagnosis = self._normalize_diagnosis(data.get("diagnosis", []))
        risks = self._normalize_risks(data.get("risks", []))
        preliminary_report = str(data.get("report", "")).strip()

        return ClinicalUnderstandingResult(
            entities=entities,
            diagnosis=diagnosis,
            risks=risks,
            preliminary_report=preliminary_report,
        )

    def _extract_json(self, content: str) -> dict:
        normalized = content.strip()
        # Strip thinking blocks emitted by reasoning models (e.g. MedGemma 1.5).
        # Handles <think>...</think> and the raw Unicode private-use token variants.
        normalized = re.sub(r"<think>.*?</think>", "", normalized, flags=re.DOTALL | re.IGNORECASE)
        # Ollama sometimes surfaces the tokens as \ufffd-range private chars; strip those too.
        normalized = re.sub(r"[\ue05e\ue05f].*?[\ue05e\ue05f]", "", normalized, flags=re.DOTALL)
        normalized = normalized.strip()
        # Strip markdown code fences if present.
        if normalized.startswith("```"):
            normalized = normalized.split("```", 2)[1]
            normalized = normalized.removeprefix("json").strip()
        start = normalized.find("{")
        if start == -1:
            raise ValueError("MedGemma understanding stage returned non-JSON content.")
        # Use raw_decode so we stop at the first complete JSON object and ignore
        # any trailing text or extra JSON blocks that cause "Extra data" errors.
        obj, _ = json.JSONDecoder().raw_decode(normalized, start)
        if not isinstance(obj, dict):
            raise ValueError("MedGemma understanding stage returned non-object JSON.")
        log.debug("[understanding] parsed_keys=%s", list(obj.keys()))
        return obj

    def _normalize_list(self, items: object, restrict_types: tuple[str, ...] | None = None) -> list[str]:
        if not isinstance(items, list):
            return []
        values = [normalize_entity_label(str(item).strip(), restrict_types) for item in items if str(item).strip()]
        return list(dict.fromkeys(values))

    def _normalize_diagnosis(self, items: object) -> list[DiagnosisSuggestion]:
        if not isinstance(items, list):
            return []
        suggestions: list[DiagnosisSuggestion] = []
        for item in items:
            if isinstance(item, dict):
                label = str(item.get("label", "")).strip()
                if not label:
                    continue
                suggestions.append(
                    DiagnosisSuggestion(
                        label=label,
                        probability=float(item.get("probability", 0.7)),
                        rationale=str(item.get("rationale", "Generated by MedGemma understanding stage.")).strip(),
                    )
                )
            else:
                label = str(item).strip()
                if label:
                    suggestions.append(
                        DiagnosisSuggestion(
                            label=label,
                            probability=0.7,
                            rationale="Generated by MedGemma understanding stage.",
                        )
                    )
        return suggestions[:5]

    def _normalize_risks(self, items: object) -> list[RiskSignal]:
        if not isinstance(items, list):
            return []
        normalized: list[RiskSignal] = []
        for item in items:
            if isinstance(item, dict):
                label = str(item.get("label", "")).strip()
                if not label:
                    continue
                severity = str(item.get("severity", "moderate")).strip().lower()
                if severity not in {"low", "moderate", "high"}:
                    severity = "moderate"
                normalized.append(
                    RiskSignal(
                        label=label,
                        severity=severity,
                        rationale=str(item.get("rationale", "Generated by MedGemma understanding stage.")).strip(),
                    )
                )
            else:
                label = str(item).strip()
                if label:
                    normalized.append(
                        RiskSignal(
                            label=label,
                            severity="moderate",
                            rationale="Generated by MedGemma understanding stage.",
                        )
                    )
        return normalized[:5]


class FallbackClinicalUnderstandingService(ClinicalUnderstandingService):
    def __init__(self) -> None:
        self.extractor = ClinicalNlpService()
        self.diagnosis = DiagnosisService()
        self.risks = RiskDetectionService()

    def analyze(self, text: str, *, images: list[str] | None = None) -> ClinicalUnderstandingResult:
        mentions = self.extractor.extract(text)
        entities = ClinicalEntities(
            diseases=self._labels_for_type(mentions, "disease"),
            symptoms=self._labels_for_type(mentions, "symptom"),
            severity=self._labels_for_type(mentions, "severity"),
            negations=self._negated_labels(mentions),
            complications=self._labels_for_type(mentions, "complication"),
        )
        return ClinicalUnderstandingResult(
            entities=entities,
            diagnosis=self.diagnosis.suggest(mentions),
            risks=self.risks.detect(mentions),
            mentions=mentions,
        )

    def _labels_for_type(self, mentions: list, entity_type: str) -> list[str]:
        values = [
            mention.label
            for mention in mentions
            if mention.entity_type == entity_type and not mention.negated
        ]
        return list(dict.fromkeys(values))

    def _negated_labels(self, mentions: list) -> list[str]:
        values = [mention.label for mention in mentions if mention.negated]
        return list(dict.fromkeys(values))

