"""FAISS-based ICD-10 vector retriever.

Loaded once at startup, then used per-request to do approximate nearest-neighbour
search over ~95 k ICD-10-CM descriptions.  Returns the top-k most semantically
similar codes as IcdPredictionCandidate objects.

The index is built offline by running:
    python scripts/build_icd_index.py
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.config import settings
from app.domain.schemas import IcdPredictionCandidate

log = logging.getLogger(__name__)


def _format_icd_code(code: str) -> str:
    """Insert the standard dot after position 3 if missing.

    ICD-10-CM codes in the raw index omit the dot (e.g. 'J45991').
    The canonical display format requires it (e.g. 'J45.991').
    """
    code = code.strip()
    if len(code) > 3 and "." not in code:
        return code[:3] + "." + code[3:]
    return code


class IcdVectorRetriever:
    """Wraps a FAISS flat-IP index + sentence-transformer encoder.

    Thread-safe for concurrent reads after warm_up() completes.
    """

    def __init__(self) -> None:
        self._model = None
        self._index = None
        self._codes: list[dict[str, str]] = []

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def warm_up(self) -> None:
        if self._model is not None:
            return

        index_dir = Path(settings.icd_index_path)
        index_file = index_dir / "index.faiss"
        codes_file = index_dir / "codes.json"

        if not index_file.exists() or not codes_file.exists():
            log.warning(
                "[retriever] FAISS index not found at %s — run "
                "'python scripts/build_icd_index.py' to build it.",
                index_dir,
            )
            return

        try:
            import faiss
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            log.warning(
                "[retriever] warm_up skipped — missing dependency: %s. "
                "Run: pip install faiss-cpu sentence-transformers",
                exc,
            )
            return

        log.info("[retriever] loading embedding model %s", settings.icd_retriever_model)
        self._model = SentenceTransformer(settings.icd_retriever_model)

        log.info("[retriever] loading FAISS index from %s", index_file)
        self._index = faiss.read_index(str(index_file))

        self._codes = json.loads(codes_file.read_text(encoding="utf-8"))
        log.info(
            "[retriever] ready  vectors=%d  codes=%d",
            self._index.ntotal,
            len(self._codes),
        )

    # ------------------------------------------------------------------ #
    # Retrieval                                                            #
    # ------------------------------------------------------------------ #

    @property
    def available(self) -> bool:
        return self._index is not None and self._model is not None

    def retrieve(
        self,
        query: str,
        k: int | None = None,
    ) -> list[IcdPredictionCandidate]:
        """Return top-k ICD candidates by cosine similarity to *query*."""
        if not self.available:
            return []

        import numpy as np

        k = k or settings.icd_retrieval_k
        vec = self._model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype(np.float32)

        scores, indices = self._index.search(vec, k)

        candidates: list[IcdPredictionCandidate] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._codes):
                continue
            entry = self._codes[idx]
            candidates.append(
                IcdPredictionCandidate(
                    code=_format_icd_code(entry["code"]),
                    description=entry["description"],
                    # Cosine similarity ∈ [-1, 1]; clamp to [0, 0.99].
                    confidence=round(min(max(float(score), 0.0), 0.99), 4),
                    evidence=[],
                )
            )
        return candidates
