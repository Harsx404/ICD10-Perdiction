"""One-time script to build a FAISS index over the full ICD-10-CM dataset.
Usage:
    python scripts/build_icd_index.py
Input:
    Dataset/icd10orderfiles/icd10cm_codes_2026.txt

Output (saved to models/icd_index/):
    index.faiss   — FAISS flat-IP index
    codes.json    — list of {"code": ..., "description": ...} in index order

The embedding model (all-MiniLM-L6-v2, ~80 MB) is downloaded from HuggingFace
on first run and cached in the default HF cache directory.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "Dataset" / "icd10orderfiles" / "icd10cm_codes_2026.txt"
OUTPUT_DIR = REPO_ROOT / "models" / "icd_index"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 512


def load_codes(path: Path) -> list[dict[str, str]]:
    """Parse icd10cm_codes_2026.txt → list of {code, description}."""
    records: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            code, description = parts
            records.append({"code": code.strip(), "description": description.strip()})
    log.info("Loaded %d ICD-10 codes from %s", len(records), path)
    return records


def build_index(records: list[dict[str, str]]) -> None:
    try:
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        log.error(
            "Missing dependency: %s\n"
            "Run: pip install faiss-cpu sentence-transformers",
            exc,
        )
        sys.exit(1)

    log.info("Loading embedding model: %s", EMBEDDING_MODEL)
    model = SentenceTransformer(EMBEDDING_MODEL)

    descriptions = [r["description"] for r in records]
    log.info("Embedding %d descriptions in batches of %d...", len(descriptions), BATCH_SIZE)

    embeddings = model.encode(
        descriptions,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,  # required for inner-product = cosine similarity
        convert_to_numpy=True,
    )
    embeddings = embeddings.astype(np.float32)

    dim = embeddings.shape[1]
    log.info("Embedding dim=%d, building FAISS IndexFlatIP...", dim)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    log.info("Index contains %d vectors", index.ntotal)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(OUTPUT_DIR / "index.faiss"))
    (OUTPUT_DIR / "codes.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("Saved index to %s", OUTPUT_DIR)

if __name__ == "__main__":
    if not DATASET_PATH.exists():
        log.error("Dataset not found: %s", DATASET_PATH)
        sys.exit(1)
    records = load_codes(DATASET_PATH)
    build_index(records)
    log.info("Done. Run the FastAPI server — the retriever will load the index at startup.")
