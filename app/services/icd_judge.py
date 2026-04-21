"""ICD-10 Judge — asks Gemma to pick the single best code from candidates.

After the FAISS retriever + rule engine produce a ranked list of ICD codes,
this service sends the clinical note and the candidate list to the local Gemma
LLM (via Ollama) and asks it to select the most clinically appropriate code
with a brief rationale.

If Gemma is unavailable or returns an unparseable response the service falls
back silently to the highest-confidence candidate from the rule engine.
"""

from __future__ import annotations

import json
import logging
import re

import httpx

from app.core.config import settings
from app.domain.schemas import DiagnosisSuggestion, IcdCode, PrimaryIcdCode

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a clinical coding expert. Given a clinical note and a list of "
    "candidate ICD-10-CM codes, select the SINGLE most appropriate code for "
    "this patient's primary diagnosis. Return ONLY valid JSON in this exact "
    'shape: {"code": "X00.0", "rationale": "one sentence explanation"}. '
    "Do not include any other text."
)


class IcdJudgeService:
    """Asks the local Gemma model to pick the best ICD code from candidates."""

    def judge(
        self,
        note_text: str,
        candidates: list[IcdCode],
        diagnosis: list[DiagnosisSuggestion] | None = None,
    ) -> PrimaryIcdCode | None:
        if not candidates:
            return None

        if not settings.enable_medgemma:
            return self._fallback(candidates, diagnosis)

        code_list = "\n".join(
            f"- {c.code}: {c.description} (confidence {c.confidence:.0%})"
            for c in candidates
        )
        diag_hint = ""
        if diagnosis:
            top = [d for d in diagnosis if d.probability >= 0.70]
            if top:
                diag_hint = (
                    "\n\nExtracted clinical diagnoses (use these to guide your selection):\n"
                    + "\n".join(
                        f"- {d.label} ({d.probability:.0%} probability)"
                        for d in top
                    )
                )
        user_content = (
            f"Clinical note:\n{note_text or '(image-only encounter)'}"
            f"{diag_hint}\n\n"
            f"Candidate ICD-10 codes:\n{code_list}\n\n"
            "Select the single best primary code that matches the diagnosed condition."
        )

        try:
            response = httpx.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": settings.llm_model,
                    "stream": False,
                    "think": False,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                },
                timeout=60.0,
            )
            response.raise_for_status()
            content = response.json().get("message", {}).get("content", "")
            log.info("[icd-judge] raw=%r", content[:200])
            return self._parse(content, candidates)
        except Exception as exc:
            log.warning("[icd-judge] failed, using fallback: %s", exc)
            return self._fallback(candidates)

    # ------------------------------------------------------------------ #

    def _parse(self, content: str, candidates: list[IcdCode]) -> PrimaryIcdCode:
        """Extract JSON from Gemma response; fall back on parse failure."""
        # Strip markdown code fences if present
        cleaned = re.sub(r"```(?:json)?|```", "", content).strip()
        # Grab the first {...} block
        match = re.search(r"\{[^}]+\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                code_val = str(data.get("code", "")).strip()
                rationale = str(data.get("rationale", "")).strip()
                # Find the matching candidate for description + confidence
                for c in candidates:
                    if c.code == code_val:
                        return PrimaryIcdCode(
                            code=c.code,
                            description=c.description,
                            confidence=c.confidence,
                            rationale=rationale,
                        )
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
        log.warning("[icd-judge] parse failed, using fallback")
        return self._fallback(candidates, diagnosis)

    def _fallback(
        self,
        candidates: list[IcdCode],
        diagnosis: list[DiagnosisSuggestion] | None = None,
    ) -> PrimaryIcdCode:
        # If we have a high-confidence diagnosis, prefer the candidate whose
        # description best matches a diagnosed label over raw confidence score.
        if diagnosis:
            from app.services.catalog import ALIAS_TO_LABEL, TERM_LOOKUP  # noqa: PLC0415
            for diag in sorted(diagnosis, key=lambda d: d.probability, reverse=True):
                if diag.probability < 0.70:
                    break
                norm_label = ALIAS_TO_LABEL.get(diag.label.lower(), diag.label.lower())
                item = TERM_LOOKUP.get(norm_label)
                if item and "icd_code" in item:
                    for c in candidates:
                        if c.code == item["icd_code"]:
                            return PrimaryIcdCode(
                                code=c.code,
                                description=c.description,
                                confidence=c.confidence,
                                rationale=f"Matched to extracted diagnosis: {diag.label}.",
                            )
        best = max(candidates, key=lambda c: c.confidence)
        return PrimaryIcdCode(
            code=best.code,
            description=best.description,
            confidence=best.confidence,
            rationale="Highest-confidence candidate selected automatically.",
        )
