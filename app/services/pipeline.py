import json
import logging
import time
from typing import Generator

from app.domain.schemas import ClinicalAnalysisResponse, ClinicalNoteRequest
from app.domain.schemas import FinalClinicalContext

log = logging.getLogger(__name__)
from app.services.icd_prediction import (
    BioBertIcdPredictionService,
    BioGptIcdPredictionService,
    BioGptReranker,
    FaissIcdPredictionService,
    FallbackIcdPredictionService,
    IcdPredictionService,
)
from app.services.retriever import IcdVectorRetriever
from app.services.reporting import (
    ClinicalReportService,
    FallbackClinicalReportService,
    MedGemmaClinicalReportService,
)
from app.services.icd_judge import IcdJudgeService
from app.services.rules import RuleEngineService
from app.services.understanding import (
    ClinicalUnderstandingService,
    FallbackClinicalUnderstandingService,
    MedGemmaClinicalUnderstandingService,
)


class ClinicalAnalysisPipeline:
    def __init__(
        self,
        understanding_service: ClinicalUnderstandingService | None = None,
        fallback_understanding_service: ClinicalUnderstandingService | None = None,
        icd_prediction_service: IcdPredictionService | None = None,
        fallback_icd_prediction_service: IcdPredictionService | None = None,
        rule_engine: RuleEngineService | None = None,
        icd_judge: IcdJudgeService | None = None,
        report_service: ClinicalReportService | None = None,
        fallback_report_service: ClinicalReportService | None = None,
    ) -> None:
        self.understanding_service = understanding_service or MedGemmaClinicalUnderstandingService()
        self.fallback_understanding_service = (
            fallback_understanding_service or FallbackClinicalUnderstandingService()
        )
        self.icd_prediction_service = icd_prediction_service or FaissIcdPredictionService(
            retriever=IcdVectorRetriever(),
            reranker=BioGptReranker(),
        )
        self.fallback_icd_prediction_service = (
            fallback_icd_prediction_service or FallbackIcdPredictionService()
        )
        self.rule_engine = rule_engine or RuleEngineService()
        self.icd_judge = icd_judge or IcdJudgeService()
        self.report_service = report_service or MedGemmaClinicalReportService()
        self.fallback_report_service = fallback_report_service or FallbackClinicalReportService()

    def run(self, payload: ClinicalNoteRequest) -> ClinicalAnalysisResponse:
        validation_notes: list[str] = []
        mode = "full"
        pipeline_start = time.perf_counter()

        # ── Stage 1: Clinical understanding ──────────────────────────────────
        log.info("[pipeline] stage=understanding status=start")
        t = time.perf_counter()
        try:
            understanding = self.understanding_service.analyze(payload.note_text, images=payload.images)
            log.info(
                "[pipeline] stage=understanding status=ok elapsed=%.2fs "
                "diseases=%s complications=%s",
                time.perf_counter() - t,
                understanding.entities.diseases,
                understanding.entities.complications,
            )
        except Exception as exc:
            log.warning("[pipeline] stage=understanding status=fallback elapsed=%.2fs error=%s", time.perf_counter() - t, exc)
            mode = "degraded"
            validation_notes.append(f"MedGemma understanding stage fallback activated: {exc}")
            understanding = self.fallback_understanding_service.analyze(payload.note_text)
            log.info(
                "[pipeline] stage=understanding-fallback status=ok diseases=%s",
                understanding.entities.diseases,
            )

        # ── Stage 2: ICD prediction ───────────────────────────────────────────
        log.info("[pipeline] stage=icd-prediction status=start")
        t = time.perf_counter()
        try:
            candidates = self.icd_prediction_service.predict(payload.note_text, understanding)
            log.info(
                "[pipeline] stage=icd-prediction status=ok elapsed=%.2fs candidates=%d",
                time.perf_counter() - t,
                len(candidates),
            )
        except Exception as exc:
            log.warning("[pipeline] stage=icd-prediction status=fallback elapsed=%.2fs error=%s", time.perf_counter() - t, exc)
            mode = "degraded"
            validation_notes.append(f"BioBERT ICD stage fallback activated: {exc}")
            candidates = self.fallback_icd_prediction_service.predict(payload.note_text, understanding)
            log.info("[pipeline] stage=icd-prediction-fallback status=ok candidates=%d", len(candidates))

        # ── Stage 3: Rule engine ──────────────────────────────────────────────
        log.info("[pipeline] stage=rule-engine status=start")
        t = time.perf_counter()
        validated_codes, rule_notes = self.rule_engine.validate(understanding, candidates)
        validation_notes.extend(rule_notes)
        log.info(
            "[pipeline] stage=rule-engine status=ok elapsed=%.2fs codes=%s",
            time.perf_counter() - t,
            [c.code for c in validated_codes],
        )

        # ── Stage 3.5: ICD Judge (Gemma picks the single best code) ──────────
        log.info("[pipeline] stage=icd-judge status=start")
        t = time.perf_counter()
        primary_icd_code = self.icd_judge.judge(
            payload.note_text, validated_codes, diagnosis=understanding.diagnosis
        )
        log.info(
            "[pipeline] stage=icd-judge status=ok elapsed=%.2fs primary=%s",
            time.perf_counter() - t,
            primary_icd_code.code if primary_icd_code else None,
        )

        report_context = FinalClinicalContext(
            note_text=payload.note_text,
            mode=mode,
            entities=understanding.entities,
            diagnosis=understanding.diagnosis,
            risks=understanding.risks,
            icd_codes=validated_codes,
            validation_notes=validation_notes,
        )

        # ── Stage 4: Report generation ────────────────────────────────────────
        log.info("[pipeline] stage=report status=start")
        t = time.perf_counter()
        if understanding.preliminary_report:
            # Report was already produced inside the Stage 1 LLM call — skip the
            # second cloud round-trip and just append the finalised ICD codes.
            icd_suffix = ""
            if validated_codes:
                codes_str = ", ".join(
                    f"{c.code} – {c.description}" for c in validated_codes
                )
                icd_suffix = f"\n\nICD-10 Codes: {codes_str}"
            report = understanding.preliminary_report + icd_suffix
            log.info("[pipeline] stage=report status=skipped-merged elapsed=%.2fs", time.perf_counter() - t)
        else:
            try:
                report = self.report_service.generate(report_context)
                log.info("[pipeline] stage=report status=ok elapsed=%.2fs", time.perf_counter() - t)
            except Exception as exc:
                log.warning("[pipeline] stage=report status=fallback elapsed=%.2fs error=%s", time.perf_counter() - t, exc)
                mode = "degraded"
                validation_notes.append(f"MedGemma report stage fallback activated: {exc}")
                report_context.mode = mode
                report_context.validation_notes = validation_notes
                report = self.fallback_report_service.generate(report_context)

        log.info("[pipeline] status=complete total=%.2fs mode=%s", time.perf_counter() - pipeline_start, mode)

        return ClinicalAnalysisResponse(
            mode=mode,
            entities=understanding.entities,
            icd_codes=validated_codes,
            primary_icd_code=primary_icd_code,
            diagnosis=understanding.diagnosis,
            risks=understanding.risks,
            report=report,
            validation_notes=validation_notes,
        )

    # ── Streaming variant for SSE ─────────────────────────────────────────
    def _sse(self, event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    def run_stream(self, payload: ClinicalNoteRequest) -> Generator[str, None, None]:
        validation_notes: list[str] = []
        mode = "full"
        pipeline_start = time.perf_counter()

        # Stage 1
        yield self._sse("stage", {"id": "understanding", "status": "running"})
        t = time.perf_counter()
        try:
            understanding = self.understanding_service.analyze(payload.note_text, images=payload.images)
            elapsed = time.perf_counter() - t
            yield self._sse("stage", {
                "id": "understanding", "status": "complete", "elapsed": round(elapsed, 2),
                "substep": f"Extracted {len(understanding.entities.diseases)} diseases, {len(understanding.entities.symptoms)} symptoms",
            })
        except Exception as exc:
            elapsed = time.perf_counter() - t
            mode = "degraded"
            validation_notes.append(f"MedGemma understanding stage fallback activated: {exc}")
            understanding = self.fallback_understanding_service.analyze(payload.note_text)
            yield self._sse("stage", {
                "id": "understanding", "status": "complete", "elapsed": round(elapsed, 2),
                "detail": "Used fallback",
            })

        # Stage 2
        yield self._sse("stage", {"id": "icd-prediction", "status": "running"})
        t = time.perf_counter()
        try:
            candidates = self.icd_prediction_service.predict(payload.note_text, understanding)
            elapsed = time.perf_counter() - t
            yield self._sse("stage", {
                "id": "icd-prediction", "status": "complete", "elapsed": round(elapsed, 2),
                "substep": f"FAISS retrieved candidates, BioGPT reranked to {len(candidates)}",
            })
        except Exception as exc:
            elapsed = time.perf_counter() - t
            mode = "degraded"
            validation_notes.append(f"ICD stage fallback activated: {exc}")
            candidates = self.fallback_icd_prediction_service.predict(payload.note_text, understanding)
            yield self._sse("stage", {
                "id": "icd-prediction", "status": "complete", "elapsed": round(elapsed, 2),
                "detail": "Used fallback",
            })

        # Stage 3
        yield self._sse("stage", {"id": "rule-engine", "status": "running"})
        t = time.perf_counter()
        validated_codes, rule_notes = self.rule_engine.validate(understanding, candidates)
        validation_notes.extend(rule_notes)
        elapsed = time.perf_counter() - t
        yield self._sse("stage", {
            "id": "rule-engine", "status": "complete", "elapsed": round(elapsed, 2),
            "substep": f"Validated {len(validated_codes)} codes, {len(rule_notes)} rule notes",
        })

        # Stage 3.5: Judge
        yield self._sse("stage", {"id": "icd-judge", "status": "running"})
        t = time.perf_counter()
        primary_icd_code = self.icd_judge.judge(
            payload.note_text, validated_codes, diagnosis=understanding.diagnosis
        )
        elapsed = time.perf_counter() - t
        yield self._sse("stage", {
            "id": "icd-judge", "status": "complete", "elapsed": round(elapsed, 2),
            "substep": f"Primary code: {primary_icd_code.code if primary_icd_code else 'none'}",
        })

        report_context = FinalClinicalContext(
            note_text=payload.note_text,
            mode=mode,
            entities=understanding.entities,
            diagnosis=understanding.diagnosis,
            risks=understanding.risks,
            icd_codes=validated_codes,
            validation_notes=validation_notes,
        )

        # Stage 4
        yield self._sse("stage", {"id": "report", "status": "running"})
        t = time.perf_counter()
        if understanding.preliminary_report:
            icd_suffix = ""
            if validated_codes:
                codes_str = ", ".join(f"{c.code} – {c.description}" for c in validated_codes)
                icd_suffix = f"\n\nICD-10 Codes: {codes_str}"
            report = understanding.preliminary_report + icd_suffix
        else:
            try:
                report = self.report_service.generate(report_context)
            except Exception as exc:
                mode = "degraded"
                validation_notes.append(f"MedGemma report stage fallback activated: {exc}")
                report_context.mode = mode
                report_context.validation_notes = validation_notes
                report = self.fallback_report_service.generate(report_context)
        elapsed = time.perf_counter() - t
        yield self._sse("stage", {"id": "report", "status": "complete", "elapsed": round(elapsed, 2)})

        # Final result
        result = ClinicalAnalysisResponse(
            mode=mode,
            entities=understanding.entities,
            icd_codes=validated_codes,
            primary_icd_code=primary_icd_code,
            diagnosis=understanding.diagnosis,
            risks=understanding.risks,
            report=report,
            validation_notes=validation_notes,
        )
        yield self._sse("result", result.model_dump())
