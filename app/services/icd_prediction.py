from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import settings
from app.domain.schemas import ClinicalUnderstandingResult, IcdPredictionCandidate
from app.services.catalog import (
    ALIAS_TO_LABEL,
    ICD_CODE_TO_DESCRIPTION,
    ICD_CODE_TO_LABEL,
    ICD_TERM_CATALOG,
    TERM_LOOKUP,
)
from app.services.retriever import IcdVectorRetriever


class IcdPredictionService(ABC):
    @abstractmethod
    def predict(
        self,
        text: str,
        understanding: ClinicalUnderstandingResult,
    ) -> list[IcdPredictionCandidate]:
        raise NotImplementedError


class BioGptReranker:
    """Re-ranks ICD candidates using BioGPT log-likelihood scoring.

    For each candidate it scores P(icd_description | clinical_context) via
    the causal-LM loss, then blends that score with the BioBERT cosine
    confidence. Lower loss = higher biomedical plausibility.
    """

    def __init__(self) -> None:
        self._tokenizer = None
        self._model = None

    def warm_up(self) -> None:
        import logging
        _log = logging.getLogger(__name__)
        if not settings.enable_biogpt:
            _log.info("[biogpt] warm_up skipped (ENABLE_BIOGPT=false)")
            return
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            _log.warning("[biogpt] warm_up skipped: %s", exc)
            return
        if self._tokenizer is None:
            _log.info("[biogpt] loading %s", settings.biogpt_model_name)
            self._tokenizer = AutoTokenizer.from_pretrained(settings.biogpt_model_name)
            self._model = AutoModelForCausalLM.from_pretrained(
                settings.biogpt_model_name,
                dtype="auto",
            )
            self._model.eval()
            _log.info("[biogpt] warm_up complete")

    def rerank(
        self,
        clinical_text: str,
        candidates: list[IcdPredictionCandidate],
        alpha: float = 0.4,
    ) -> list[IcdPredictionCandidate]:
        """Blend BioBERT confidence (1-alpha) with BioGPT log-likelihood (alpha)."""
        if not candidates or not settings.enable_biogpt or self._model is None:
            return candidates

        import torch

        raw_scores: list[float] = []
        for c in candidates:
            prompt = (
                f"Clinical note: {clinical_text[:300]} "
                f"ICD-10 diagnosis: {c.description}"
            )
            tokens = self._tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )
            with torch.no_grad():
                loss = self._model(**tokens, labels=tokens["input_ids"]).loss
            raw_scores.append(-float(loss.item()))  # higher = more plausible

        lo, hi = min(raw_scores), max(raw_scores)
        span = hi - lo if hi != lo else 1.0
        norm = [(s - lo) / span for s in raw_scores]

        reranked = [
            c.model_copy(update={"confidence": round((1 - alpha) * c.confidence + alpha * bg, 4)})
            for c, bg in zip(candidates, norm)
        ]
        reranked.sort(key=lambda c: c.confidence, reverse=True)
        return reranked


class BioGptIcdPredictionService(IcdPredictionService):
    """ICD-10 prediction via BioGPT log-likelihood scoring over the full catalog.

    For every entry in ICD_TERM_CATALOG it computes
    P(icd_description | clinical_context) using the BioGPT causal-LM loss,
    then normalises the scores, applies alias-entity boosting, and returns
    the top-k codes.  No weights file is required beyond the BioGPT download.
    """

    def __init__(self, reranker: BioGptReranker) -> None:
        self._reranker = reranker

    def warm_up(self) -> None:
        self._reranker.warm_up()

    def predict(
        self,
        text: str,
        understanding: ClinicalUnderstandingResult,
    ) -> list[IcdPredictionCandidate]:
        if not settings.enable_biogpt:
            raise RuntimeError("BioGPT ICD stage is disabled.")

        self.warm_up()

        model = self._reranker._model
        tokenizer = self._reranker._tokenizer
        if model is None or tokenizer is None:
            raise RuntimeError("BioGPT model failed to load during warm_up.")

        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("torch is not installed.") from exc

        diagnosis_labels = [
            d.label.lower()
            for d in understanding.diagnosis
            if d.probability >= 0.5
        ]
        positive_labels = set(
            understanding.entities.diseases
            + understanding.entities.symptoms
            + understanding.entities.complications
            + diagnosis_labels
        )
        normalized_positive = {
            ALIAS_TO_LABEL.get(lbl.lower(), lbl) for lbl in positive_labels
        }

        relevance_text = " ".join([
            text,
            " ".join(understanding.entities.diseases),
            " ".join(understanding.entities.symptoms),
            " ".join(understanding.entities.complications),
            " ".join(diagnosis_labels),
        ]).strip()

        # Score every catalog entry via BioGPT log-likelihood.
        raw_scores: list[float] = []
        for item in ICD_TERM_CATALOG:
            prompt = (
                f"Clinical note: {relevance_text[:300]} "
                f"ICD-10 diagnosis: {item['icd_description']}"
            )
            tokens = tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )
            with torch.no_grad():
                loss = model(**tokens, labels=tokens["input_ids"]).loss
            raw_scores.append(-float(loss.item()))  # higher = more plausible

        lo, hi = min(raw_scores), max(raw_scores)
        span = hi - lo if hi != lo else 1.0

        candidates: list[IcdPredictionCandidate] = []
        for item, score in zip(ICD_TERM_CATALOG, raw_scores):
            confidence = (score - lo) / span
            if item["label"] in normalized_positive:
                confidence = min(confidence + 0.2, 0.99)
            evidence = (
                [item["label"]]
                if item["label"] in normalized_positive
                else sorted(positive_labels)[:2]
            )
            candidates.append(
                IcdPredictionCandidate(
                    code=item["icd_code"],
                    description=item["icd_description"],
                    confidence=round(min(confidence, 0.99), 4),
                    evidence=evidence,
                )
            )

        candidates.sort(key=lambda c: c.confidence, reverse=True)
        return candidates[: settings.icd_top_k]


class BioBertIcdPredictionService(IcdPredictionService):
    """Clinical-BERT fine-tuned ICD-10 classifier.

    Uses AutoModelForSequenceClassification with the full fine-tuned
    classification head (thousands of ICD-10 codes) instead of cosine
    similarity over a small catalog. The model's id2label maps logit
    indices directly to ICD codes.
    """

    def __init__(self, reranker: BioGptReranker | None = None) -> None:
        self._tokenizer = None
        self._model = None
        self._id2label: dict[int, str] | None = None
        self._reranker = reranker

    def warm_up(self) -> None:
        import logging
        _log = logging.getLogger(__name__)
        if not settings.enable_icd_model:
            _log.info("[icd_prediction] warm_up skipped (ENABLE_ICD_MODEL=false)")
            return
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            _log.warning("[icd_prediction] warm_up skipped: %s", exc)
            return
        if self._tokenizer is None or self._model is None:
            _log.info("[icd_prediction] warm_up loading classifier %s", settings.icd_model_name)
            self._tokenizer = AutoTokenizer.from_pretrained(settings.icd_model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                settings.icd_model_name,
                dtype="auto",
            )
            self._model.eval()
            self._id2label = {int(k): v for k, v in self._model.config.id2label.items()}
            _log.info("[icd_prediction] warm_up complete labels=%d", len(self._id2label))
        if self._reranker:
            self._reranker.warm_up()

    def predict(
        self,
        text: str,
        understanding: ClinicalUnderstandingResult,
    ) -> list[IcdPredictionCandidate]:
        if not settings.enable_icd_model:
            raise RuntimeError("Clinical-BERT ICD stage is disabled.")
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("torch is not installed.") from exc

        self.warm_up()

        if self._model is None or self._tokenizer is None or self._id2label is None:
            raise RuntimeError("ICD model failed to load during warm_up.")

        diagnosis_labels = [
            d.label.lower()
            for d in understanding.diagnosis
            if d.probability >= 0.5
        ]
        positive_labels = set(
            understanding.entities.diseases
            + understanding.entities.symptoms
            + understanding.entities.complications
            + diagnosis_labels
        )
        if not positive_labels:
            return []

        relevance_text = " ".join([
            text,
            " ".join(understanding.entities.diseases),
            " ".join(understanding.entities.symptoms),
            " ".join(understanding.entities.complications),
            " ".join(understanding.entities.severity),
            " ".join(diagnosis_labels),
        ]).strip()

        normalized_positive = {
            ALIAS_TO_LABEL.get(lbl.lower(), lbl) for lbl in positive_labels
        }

        tokens = self._tokenizer(
            relevance_text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        with torch.no_grad():
            logits = self._model(**tokens).logits[0]  # shape: (num_labels,)

        probs = torch.softmax(logits, dim=-1)
        pool_size = settings.icd_top_k * 4 if self._reranker else settings.icd_top_k
        top_indices = probs.argsort(descending=True)[: pool_size * 2].tolist()

        candidates: list[IcdPredictionCandidate] = []
        for idx in top_indices:
            code = self._id2label[idx]
            confidence = float(probs[idx].item())
            if confidence < 0.001:
                continue

            description = ICD_CODE_TO_DESCRIPTION.get(code, f"ICD-10 {code}")
            catalog_label = ICD_CODE_TO_LABEL.get(code)

            # Boost codes whose catalog label matches an extracted entity.
            if catalog_label and catalog_label in normalized_positive:
                confidence = min(confidence + 0.2, 0.99)

            evidence = (
                [catalog_label]
                if catalog_label and catalog_label in normalized_positive
                else sorted(positive_labels)[:2]
            )
            candidates.append(
                IcdPredictionCandidate(
                    code=code,
                    description=description,
                    confidence=min(confidence, 0.99),
                    evidence=evidence,
                )
            )
            if len(candidates) >= pool_size:
                break

        if self._reranker:
            candidates = self._reranker.rerank(relevance_text, candidates)

        return candidates[: settings.icd_top_k]


class FaissIcdPredictionService(IcdPredictionService):
    """Two-stage ICD-10 prediction: FAISS vector retrieval → BioGPT re-ranking.

    Stage 2A: embed the clinical relevance text with all-MiniLM-L6-v2, do
    ANN search over the full ~95 k ICD-10-CM index → top-K candidates.

    Stage 2B: BioGPT log-likelihood re-ranking over those candidates.
    Alias-entity boosting applied after re-ranking.
    """

    def __init__(self, retriever: IcdVectorRetriever, reranker: BioGptReranker) -> None:
        self._retriever = retriever
        self._reranker = reranker

    def warm_up(self) -> None:
        self._retriever.warm_up()
        self._reranker.warm_up()

    def predict(
        self,
        text: str,
        understanding: ClinicalUnderstandingResult,
    ) -> list[IcdPredictionCandidate]:
        if not self._retriever.available:
            raise RuntimeError(
                "FAISS index not loaded. Run 'python scripts/build_icd_index.py' first."
            )

        diagnosis_labels = [
            d.label.lower()
            for d in understanding.diagnosis
            if d.probability >= 0.5
        ]
        positive_labels = set(
            understanding.entities.diseases
            + understanding.entities.symptoms
            + understanding.entities.complications
            + diagnosis_labels
        )
        normalized_positive = {
            ALIAS_TO_LABEL.get(lbl.lower(), lbl) for lbl in positive_labels
        }

        # Strip any disease term that is also negated so it doesn't steer
        # FAISS toward codes that the rule engine will then suppress entirely.
        negation_lower = {n.lower() for n in understanding.entities.negations}
        positive_diseases = [
            d for d in understanding.entities.diseases
            if d.lower() not in negation_lower
        ]

        relevance_text = " ".join([
            text,
            " ".join(positive_diseases),
            " ".join(understanding.entities.symptoms),
            " ".join(understanding.entities.complications),
            " ".join(understanding.entities.severity),
            " ".join(diagnosis_labels),
            # Negations passed as "without X" so BioGPT naturally assigns
            # lower log-likelihood to contradicted ICD codes (soft signal).
            # The rule engine _PHRASE_SYNONYMS acts as a hard safety net.
            " ".join(
                f"without {n}" if not n.lower().startswith("without") else n
                for n in understanding.entities.negations
            ),
        ]).strip()
        candidates = self._retriever.retrieve(relevance_text, k=settings.icd_retrieval_k)

        # Inject catalog entries for high-confidence diagnosed conditions that
        # FAISS may have missed (e.g. "herpes zoster oticus" when ear symptoms
        # caused otitis media codes to dominate the vector search).
        existing_codes = {c.code for c in candidates}
        for diag in understanding.diagnosis:
            if diag.probability < 0.70:
                continue
            diag_label = ALIAS_TO_LABEL.get(diag.label.lower(), diag.label.lower())
            item = TERM_LOOKUP.get(diag_label)
            if item and "icd_code" in item and item["icd_code"] not in existing_codes:
                candidates.insert(
                    0,
                    IcdPredictionCandidate(
                        code=item["icd_code"],
                        description=item["icd_description"],
                        confidence=min(diag.probability, 0.99),
                        evidence=[diag_label],
                    ),
                )
                existing_codes.add(item["icd_code"])

        if not candidates:
            return []

        # Pre-filter negated codes BEFORE BioGPT reranking.
        # BioGPT is a causal LM — it sees "hypertension" in the prompt and
        # boosts "Hypertensive…" descriptions regardless of negation context.
        # Removing them early prevents them from crowding the top-K slots.
        if understanding.entities.negations:
            from app.services.rules import _extract_negated_phrases, _is_positive_match  # noqa: PLC0415
            negated_phrases = _extract_negated_phrases(set(understanding.entities.negations))
            if negated_phrases:
                candidates = [
                    c for c in candidates
                    if not any(_is_positive_match(p, c.description) for p in negated_phrases)
                ]

        if not candidates:
            return []

        # Stage 2B: BioGPT re-ranking (blends cosine score with log-likelihood)
        if settings.enable_biogpt and self._reranker._model is not None:
            candidates = self._reranker.rerank(relevance_text, candidates)

        # Determine whether acute exacerbation is clinically documented.
        _ACUTE_MARKERS = ("exacerbation", "acute attack", "acute worsening",
                          "status asthmaticus", "acute flare", "er visit",
                          "emergency", "rescue inhaler")
        all_findings = " ".join(
            understanding.entities.diseases
            + understanding.entities.symptoms
            + understanding.entities.complications
            + diagnosis_labels
        ).lower()
        exacerbation_documented = any(m in all_findings for m in _ACUTE_MARKERS)

        # Apply alias-entity boost post re-ranking
        boosted: list[IcdPredictionCandidate] = []
        for c in candidates:
            confidence = c.confidence
            # Check if any alias of a known catalog label matches this description
            desc_lower = c.description.lower()
            matched_label: str | None = None
            for lbl in normalized_positive:
                if lbl in desc_lower:
                    matched_label = lbl
                    confidence = min(confidence + 0.15, 0.99)
                    break

            # Penalise "family history" / "personal history" / screening Z-codes
            # when the condition is an active diagnosis (present in diseases).
            _HISTORY_MARKERS = ("family history", "personal history", "history of")
            if any(m in desc_lower for m in _HISTORY_MARKERS):
                # Only penalise when the referenced condition is actively present.
                if any(d.lower() in desc_lower for d in understanding.entities.diseases):
                    confidence = max(confidence - 0.25, 0.01)

            # Penalise exacerbation codes when no acute worsening is documented;
            # boost "uncomplicated" variants so they outrank exacerbation peers.
            if not exacerbation_documented:
                if "exacerbation" in desc_lower or "status asthmaticus" in desc_lower:
                    confidence = max(confidence - 0.20, 0.01)
                elif "uncomplicated" in desc_lower or "without exacerbation" in desc_lower:
                    confidence = min(confidence + 0.10, 0.99)

            evidence = [matched_label] if matched_label else sorted(positive_labels)[:2]
            boosted.append(
                c.model_copy(update={"confidence": round(confidence, 4), "evidence": evidence})
            )

        boosted.sort(key=lambda c: c.confidence, reverse=True)
        return boosted[: settings.icd_top_k]


class FallbackIcdPredictionService(IcdPredictionService):
    def predict(
        self,
        text: str,
        understanding: ClinicalUnderstandingResult,
    ) -> list[IcdPredictionCandidate]:
        del text
        raw_labels = understanding.entities.diseases + understanding.entities.symptoms
        # Normalize aliases (e.g. "wheezing" → "asthma") before catalog lookup.
        labels = [
            ALIAS_TO_LABEL.get(lbl.lower(), lbl.lower()) for lbl in raw_labels
        ]
        candidates: dict[str, IcdPredictionCandidate] = {}

        for label in labels:
            item = TERM_LOOKUP.get(label)
            if not item or "icd_code" not in item:
                continue

            candidate = IcdPredictionCandidate(
                code=item["icd_code"],
                description=item["icd_description"],
                confidence=0.85 if item["entity_type"] == "disease" else 0.70,
                evidence=[label],
            )
            existing = candidates.get(candidate.code)
            if existing is None or candidate.confidence > existing.confidence:
                candidates[candidate.code] = candidate

        return sorted(candidates.values(), key=lambda c: c.confidence, reverse=True)
