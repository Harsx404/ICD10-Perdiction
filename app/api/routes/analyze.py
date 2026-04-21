import base64
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse

from app.domain.schemas import ClinicalAnalysisResponse, ClinicalNoteRequest
from app.services.mongo import find_cached, get_pdf, list_analyses, make_fingerprint, save_analysis
from app.services.pdf_report import generate_pdf
from app.services.pipeline import ClinicalAnalysisPipeline

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["analysis"])
pipeline = ClinicalAnalysisPipeline()


def _fingerprint_from_response(result: ClinicalAnalysisResponse) -> str:
    diseases = result.entities.diseases
    diag_labels = [d.label for d in result.diagnosis]
    return make_fingerprint(diseases, diag_labels)


def _persist(payload: ClinicalNoteRequest, result: ClinicalAnalysisResponse) -> str | None:
    """Generate PDF and save to MongoDB. Returns doc_id or None."""
    try:
        pdf_bytes = generate_pdf(result.model_dump(), note_text=payload.note_text)
        fp = _fingerprint_from_response(result)
        return save_analysis(
            fingerprint=fp,
            note_text=payload.note_text,
            images_count=len(payload.images),
            response_dict=result.model_dump(),
            pdf_bytes=pdf_bytes,
        )
    except Exception as exc:
        log.warning("[analyze] persist failed: %s", exc)
        return None


@router.post("/analyze", response_model=ClinicalAnalysisResponse)
def analyze_note(payload: ClinicalNoteRequest) -> ClinicalAnalysisResponse:
    result = pipeline.run(payload)
    doc_id = _persist(payload, result)
    if doc_id:
        result.doc_id = doc_id
    return result


@router.post("/analyze/stream")
def analyze_stream(payload: ClinicalNoteRequest) -> StreamingResponse:
    """SSE streaming — persists after the result event and sends a doc_id event."""
    import json

    def _stream_and_save():
        for chunk in pipeline.run_stream(payload):
            yield chunk
            # Intercept the result event to persist synchronously, then emit doc_id
            if chunk.startswith("event: result\n"):
                try:
                    data_line = next(
                        (l for l in chunk.splitlines() if l.startswith("data:")), None
                    )
                    if data_line:
                        data = json.loads(data_line[5:].strip())
                        result_obj = ClinicalAnalysisResponse.model_validate(data)
                        doc_id = _persist(payload, result_obj)
                        if doc_id:
                            yield f"event: doc_id\ndata: {json.dumps({'doc_id': doc_id})}\n\n"
                except Exception as exc:
                    log.warning("[analyze-stream] parse/persist failed: %s", exc)

    return StreamingResponse(
        _stream_and_save(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/analyze/upload", response_model=ClinicalAnalysisResponse)
async def analyze_upload(
    note_text: str = Form(default=""),
    images: list[UploadFile] = File(default=[]),
) -> ClinicalAnalysisResponse:
    image_b64: list[str] = []
    for img in images:
        data = await img.read()
        image_b64.append(base64.b64encode(data).decode("ascii"))
    payload = ClinicalNoteRequest(note_text=note_text, images=image_b64)
    result = pipeline.run(payload)
    doc_id = _persist(payload, result)
    if doc_id:
        result.doc_id = doc_id
    return result


# ── History & PDF retrieval ───────────────────────────────────────────────────

@router.get("/analyses", tags=["history"])
def get_analyses(limit: int = 50) -> list[dict]:
    """List recent analyses from MongoDB (no PDF payload)."""
    return list_analyses(limit=limit)


@router.get("/analyses/{doc_id}/pdf", tags=["history"])
def get_analysis_pdf(doc_id: str) -> Response:
    """Stream the PDF report for a stored analysis."""
    pdf = get_pdf(doc_id)
    if pdf is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="report-{doc_id}.pdf"'},
    )

