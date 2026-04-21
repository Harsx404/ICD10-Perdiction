# Clinical Intelligence System

Full-stack FastAPI + React app for clinical note analysis, ICD-10 coding, optional saved PDF reports, and billing preparation. When the frontend is built, FastAPI serves the SPA at `/`; the older demo surface remains available at `/review`.

The detailed architecture lives in [docs/architecture.md](docs/architecture.md).
The model setup guide lives in [docs/model-setup.md](docs/model-setup.md).

## Latest Update

- React dashboard at `/` with routes for analysis, browser history, reports, and billing
- Streaming analysis via `POST /api/v1/analyze/stream` with live stage updates
- `ICD Judge` step that selects `primary_icd_code` after rule validation
- PDF generation plus optional saved-analysis persistence with response `doc_id`
- Browser history stored in `localStorage`, with Mongo-backed saved reports and PDFs
- Indian billing form auto-filled from analysis output, plus backend estimate and claim-verification APIs

## User Flow

1. Open the dashboard at `/` and submit note text or image uploads.
2. Watch the live pipeline stages complete in the UI.
3. Review structured entities, ICD codes, the primary ICD selection, diagnosis suggestions, risks, and report output.
4. Revisit browser-side results on `/history`.
5. Open saved PDFs on `/report` when Mongo persistence succeeds.
6. Use `/billing` to auto-fill billing details from the active analysis result.

## User-Visible Pipeline

1. `Clinical Understanding`
2. `ICD-10 Prediction`
3. `Rule Engine`
4. `ICD Judge`
5. `Report Generation`

If a model-backed stage fails, the API switches to `degraded` mode and records the fallback in `validation_notes`.

## Model Stack

- MedGemma runtime: `MedAIBase/MedGemma1.5:4b`
- ICD model default: `AkshatSurolia/ICD-10-Code-Prediction`
- Optional persistence: MongoDB via `MONGO_URI` and `MONGO_DB_NAME`

## API Surface

- `POST /api/v1/analyze` - Standard JSON analysis request
- `POST /api/v1/analyze/stream` - SSE analysis with stage-by-stage updates
- `POST /api/v1/analyze/upload` - Multipart note plus image upload analysis
- `GET /api/v1/analyses` - List saved Mongo-backed analyses
- `GET /api/v1/analyses/{doc_id}/pdf` - Stream a saved PDF report
- `POST /api/v1/billing/estimate` - ICD-based cost estimate API
- `POST /api/v1/billing/verify` - Claim verification API
- `GET /health` - Health check
- `GET /docs` - OpenAPI docs
- `GET /review` - Legacy review/demo page

## Response Shape

Typical `POST /api/v1/analyze` response:

```json
{
  "mode": "full",
  "entities": {
    "diseases": ["hypertension"],
    "symptoms": ["headache"],
    "severity": [],
    "negations": ["chest pain"],
    "complications": []
  },
  "icd_codes": [
    {
      "code": "I10",
      "description": "Essential (primary) hypertension",
      "confidence": 0.93
    }
  ],
  "primary_icd_code": {
    "code": "I10",
    "description": "Essential (primary) hypertension",
    "confidence": 0.93,
    "rationale": "Matched to extracted diagnosis: Hypertension."
  },
  "diagnosis": [
    {
      "label": "Hypertension",
      "probability": 0.91,
      "rationale": "Tracked test diagnosis."
    }
  ],
  "risks": [],
  "report": "Subjective: ...",
  "validation_notes": [],
  "doc_id": "661f2b2e4b5b123456789abc"
}
```

- `primary_icd_code` is chosen after rule validation by the `ICD Judge` step and may be `null`.
- `doc_id` is optional and only appears when PDF persistence succeeds.

## Local Setup

### Backend

Run the FastAPI app on port `8000`:

```powershell
uvicorn app.main:app --reload
```

### Frontend Dev

Run the Vite frontend on port `5173`:

```powershell
cd frontend
npm install
npm run dev
```

Vite proxies `/api` requests to `http://localhost:8000`.

### Built Frontend Through FastAPI

Build the SPA into `app/static/dist`, then serve it from FastAPI:

```powershell
cd frontend
npm install
npm run build
cd ..
uvicorn app.main:app --reload
```

Open:

- SPA dev server: `http://127.0.0.1:5173`
- Built SPA through FastAPI: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`
- Legacy review page: `http://127.0.0.1:8000/review`

## Configuration

The app auto-loads settings from the repo-root `.env` file.

Model and pipeline settings can live there, including:

- `ENABLE_MEDGEMMA`
- `ENABLE_ICD_MODEL`
- `OLLAMA_BASE_URL`
- `LLM_MODEL`
- `ICD_MODEL_NAME`
- `ENABLE_BIOGPT`
- `ICD_TOP_K`
- `ICD_INDEX_PATH`
- `ICD_RETRIEVER_MODEL`
- `ICD_RETRIEVAL_K`

Mongo-backed persistence is optional and controlled with:

- `MONGO_URI`
- `MONGO_DB_NAME`

Without Mongo persistence, analysis still works, but saved analyses, PDF retrieval, and response `doc_id` are not guaranteed.

## Persistence Notes

- `/history` uses browser `localStorage` and works without MongoDB.
- `/report` depends on saved analyses returned by `GET /api/v1/analyses`.
- `doc_id` and PDF retrieval depend on successful Mongo-backed persistence.

## Billing Notes

- The current SPA billing route is an Indian billing form auto-filled from the active analysis result.
- The backend also exposes `POST /api/v1/billing/estimate` and `POST /api/v1/billing/verify` for integrations.
- Claim verification is available at the API level, but it is not surfaced as a completed flow in the current SPA.

## Full Model Setup

For full model mode, see [docs/model-setup.md](docs/model-setup.md). The current model download commands are:

- `ollama pull MedAIBase/MedGemma1.5:4b`
- `pip install ".[models]"`
- `huggingface-cli download AkshatSurolia/ICD-10-Code-Prediction --local-dir models/icd10_prediction`

## Verification

Repo tests:

```bash
python -m pytest -q
```
