"""MongoDB persistence for clinical analyses.

Stores every completed analysis with its PDF report bytes.
Supports cache lookup by diagnosis fingerprint so repeated analyses of the
same condition skip the LLM pipeline.

Collection schema (analyses):
  {
    _id: ObjectId,
    fingerprint: str,          # sorted, lowercased disease labels hash
    note_text: str,
    images_count: int,
    response: dict,            # ClinicalAnalysisResponse.model_dump()
    pdf_b64: str,              # base64-encoded PDF bytes
    created_at: datetime,
    version: int,              # monotonically increasing per fingerprint
  }
"""

from __future__ import annotations

import base64
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

_client = None
_db = None


def _get_db():
    global _client, _db
    if _db is not None:
        return _db
    try:
        import pymongo
        from app.core.config import settings
        _client = pymongo.MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        _client.admin.command("ping")
        _db = _client[settings.mongo_db_name]
        _db["analyses"].create_index("fingerprint")
        _db["analyses"].create_index("created_at")
        log.info("[mongo] connected to %s / %s", settings.mongo_uri, settings.mongo_db_name)
    except Exception as exc:
        log.warning("[mongo] unavailable: %s — persistence disabled", exc)
        _db = None
    return _db


def make_fingerprint(diseases: list[str], diagnosis_labels: list[str]) -> str:
    """Stable hash of the primary clinical entities for cache keying."""
    terms = sorted({t.lower().strip() for t in diseases + diagnosis_labels if t.strip()})
    return hashlib.sha256("|".join(terms).encode()).hexdigest()[:16]


def save_analysis(
    fingerprint: str,
    note_text: str,
    images_count: int,
    response_dict: dict[str, Any],
    pdf_bytes: bytes,
) -> str | None:
    """Persist a completed analysis. Returns the inserted document id string."""
    db = _get_db()
    if db is None:
        return None
    try:
        existing_count = db["analyses"].count_documents({"fingerprint": fingerprint})
        doc = {
            "fingerprint": fingerprint,
            "note_text": note_text,
            "images_count": images_count,
            "response": response_dict,
            "pdf_b64": base64.b64encode(pdf_bytes).decode(),
            "created_at": datetime.now(timezone.utc),
            "version": existing_count + 1,
        }
        result = db["analyses"].insert_one(doc)
        log.info("[mongo] saved analysis id=%s fingerprint=%s version=%d", result.inserted_id, fingerprint, doc["version"])
        return str(result.inserted_id)
    except Exception as exc:
        log.warning("[mongo] save failed: %s", exc)
        return None


def find_cached(fingerprint: str) -> dict[str, Any] | None:
    """Return the most recent analysis for this fingerprint, or None."""
    db = _get_db()
    if db is None:
        return None
    try:
        doc = db["analyses"].find_one(
            {"fingerprint": fingerprint},
            sort=[("created_at", -1)],
        )
        return doc
    except Exception as exc:
        log.warning("[mongo] find failed: %s", exc)
        return None


def list_analyses(limit: int = 50) -> list[dict[str, Any]]:
    """Return recent analyses (no pdf_b64 to keep payload small)."""
    db = _get_db()
    if db is None:
        return []
    try:
        docs = list(
            db["analyses"]
            .find({}, {"pdf_b64": 0})
            .sort("created_at", -1)
            .limit(limit)
        )
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs
    except Exception as exc:
        log.warning("[mongo] list failed: %s", exc)
        return []


def get_pdf(doc_id: str) -> bytes | None:
    """Retrieve PDF bytes for a specific analysis id."""
    db = _get_db()
    if db is None:
        return None
    try:
        from bson import ObjectId
        doc = db["analyses"].find_one({"_id": ObjectId(doc_id)}, {"pdf_b64": 1})
        if doc and doc.get("pdf_b64"):
            return base64.b64decode(doc["pdf_b64"])
        return None
    except Exception as exc:
        log.warning("[mongo] get_pdf failed: %s", exc)
        return None
