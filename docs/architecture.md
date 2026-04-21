# Clinical Intelligence System — Architecture

**Version:** 0.5.0  
**Architecture:** Modular Monolith  
**API:** FastAPI + Uvicorn  

---

## System Overview

The Clinical Intelligence System accepts free-text clinical notes and produces structured ICD-10 codes, diagnosis suggestions, risk signals, and a SOAP-style clinical report. It runs a three-model AI pipeline with graceful degradation at every stage.

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Client (Browser)                            │
│                      GET /review  ·  POST /api/v1/analyze            │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ HTTP
┌────────────────────────────────▼─────────────────────────────────────┐
│                         FastAPI Application                          │
│   app/main.py  ·  app/api/router.py  ·  app/api/routes/analyze.py   │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│                      ClinicalAnalysisPipeline                        │
│                        app/services/pipeline.py                      │
│                                                                      │
│  Stage 1            Stage 2A          Stage 2B       Stage 3         │
│  ────────────        ─────────────     ──────────     ──────────     │
│  Clinical            FAISS Vector      BioGPT         Rule           │
│  Understanding       Retrieval         Re-ranking     Engine         │
│  (Gemma LLM)         (MiniLM +         (causal LM)    (Python)       │
│                       74 k codes)                                    │
│                                                                      │
│  Stage 4                                                             │
│  ────────────────────────────────                                    │
│  Report Generation  (from Stage 1 preliminary_report, no extra LLM) │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Models

| Role | Model | Location | Size |
|------|-------|----------|------|
| Clinical understanding + report | `gemma4:31b-cloud` | Ollama (remote) | cloud |
| ICD vector embedding | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace cache | ~80 MB |
| FAISS index | `IndexFlatIP` (cosine via inner product) | `models/icd_index/` | ~300 MB |
| ICD re-ranker | `microsoft/biogpt` | HuggingFace cache | ~350 MB |

---

## Stage 1 — Clinical Understanding

**Service:** `MedGemmaClinicalUnderstandingService`  
**Fallback:** `FallbackClinicalUnderstandingService` (rule-based NLP)  
**Model:** `gemma4:31b-cloud` via Ollama (`http://localhost:11434`)  
**Timeout:** 120 s  

The LLM receives the raw clinical note and returns structured JSON in a **single call** that covers both entity extraction and the preliminary SOAP report (Stage 4 reuses `preliminary_report` directly — no second LLM call):

```json
{
  "entities": {
    "diseases":       ["type 2 diabetes mellitus"],
    "symptoms":       ["shortness of breath"],
    "severity":       ["uncontrolled"],
    "negations":      ["chest pain"],
    "complications":  ["nephropathy"]
  },
  "diagnosis": [
    { "label": "...", "probability": 0.95, "rationale": "..." }
  ],
  "risks": [
    { "label": "...", "severity": "high", "rationale": "..." }
  ],
  "report": "Subjective: ... Objective: ... Assessment: ... Plan: ..."
}
```

**Diagnosis labelling rules (enforced by system prompt):**
- "Exacerbation" label only when the note explicitly documents acute worsening, ER/urgent visit, rescue inhaler use, or the word "exacerbation"
- Chronic/recurring symptoms alone → base disease label (e.g. `"Asthma"`, not `"Asthma exacerbation"`)
- `probability` reflects certainty: documented history ≥ 0.9, strongly implied 0.7–0.89, possible/risk only 0.3–0.69

**Robustness measures:**
- `"think": false` suppresses chain-of-thought tokens
- `<think>…</think>` blocks and Unicode private-use tokens are stripped via regex
- `json.JSONDecoder.raw_decode()` stops at the first complete JSON object

**Fallback path:** `ClinicalNlpService` (regex alias matching) + `DiagnosisService` + `RiskDetectionService`

**Normalization:** Every entity label is resolved through `ALIAS_TO_LABEL_BY_TYPE` (longest-alias, type-restricted match) to produce canonical catalog labels.

---

## Stage 2 — ICD-10 Prediction

**Primary service:** `FaissIcdPredictionService`  
**Fallback:** `FallbackIcdPredictionService` (small catalog lookup)  

### Stage 2A — FAISS Vector Retrieval

**Service:** `IcdVectorRetriever` (`app/services/retriever.py`)  
**Index:** `models/icd_index/index.faiss` + `models/icd_index/codes.json`  
**Codes:** 74,719 ICD-10-CM 2026 codes  
**Embedding model:** `sentence-transformers/all-MiniLM-L6-v2`  
**Retrieval K:** 100 (configurable via `ICD_RETRIEVAL_K`)  

The retriever encodes a `relevance_text` query constructed from:

```
{original note text} {positive diseases} {symptoms} {complications} {severity}
{diagnosis labels (prob ≥ 0.5)} {negations as "without X" phrases}
```

Negated disease terms are **excluded from `positive_diseases`** to prevent FAISS from steering toward codes that will later be suppressed.

The index uses `IndexFlatIP` (inner product on `normalize_embeddings=True` vectors ≡ cosine similarity). Returns top-100 candidates.

**Pre-filter (before BioGPT):** Negated codes are removed from the candidate pool before re-ranking. `_is_positive_match()` in `rules.py` uses a 50-character look-behind window to distinguish codes that *encode absence* (e.g. R030 "without diagnosis of hypertension" → kept) from codes that *encode presence* (e.g. I13xx "Hypertensive…" → removed).

### Stage 2B — BioGPT Re-ranking

**Service:** `BioGptReranker`  
**Model:** `microsoft/biogpt`  
**alpha:** 0.4 (blend weight)  

For each of the 100 surviving candidates, BioGPT computes:

```
loss = P(icd_description | "Clinical note: {relevance_text[:300]} ICD-10 diagnosis: {description}")
score = -loss   (higher = more plausible)
```

Final confidence = `(1 − 0.4) × faiss_score + 0.4 × biogpt_score`

### Post-ranking adjustments

Applied after BioGPT in order:

| Condition | Adjustment |
|-----------|-----------|
| Code description contains "family/personal history of X" and X is an active disease | −0.25 |
| No acute markers documented + code contains "exacerbation" or "status asthmaticus" | −0.20 |
| No acute markers documented + code contains "uncomplicated" or "without exacerbation" | +0.10 |
| Matched entity label present in code description | +0.15 |

**Acute markers:** `exacerbation`, `acute attack`, `acute worsening`, `status asthmaticus`, `acute flare`, `er visit`, `emergency`, `rescue inhaler`

Top-K returned (default `ICD_TOP_K=5`).

---

## Stage 3 — Rule Engine

**Service:** `RuleEngineService` (`app/services/rules.py`)  

Pure Python. No model involved. Applied to Stage 2 output.

1. **Evidence filter** — candidates whose evidence set is a subset of negated labels are removed.
2. **Deduplication** — highest-confidence candidate wins per ICD code.
3. **Negation phrase suppression** — `_extract_negated_phrases()` strips leading negation words (without/no/denies/etc.) and expands via `_PHRASE_SYNONYMS`:

   | Negated phrase | Also suppresses |
   |----------------|----------------|
   | `hypertension` | `hypertensive` |
   | `complication` | `exacerbation`, `status asthmaticus`, `with acute` |
   | `exacerbation` | `status asthmaticus`, `with acute`, `complication` |
   | `infection` | `infectious`, `sepsis`, `bacteremia` |

   `_is_positive_match(phrase, description)` uses a 50-character look-behind to preserve codes that encode *absence* of the negated finding.

4. **Disease-code prioritization** — codes mapped to extracted disease entities are sorted to the top.
5. **Combination rules** — co-occurrence of disease + complication triggers a more specific combined code.

Returns best 3 validated codes.

---

## Stage 4 — Report Generation

**Service:** `MedGemmaClinicalReportService`  
**Fallback:** `FallbackClinicalReportService` → `DocumentationService`  

Stage 4 **does not make a second LLM call** when Stage 1 produced a `preliminary_report`. The SOAP narrative from the Stage 1 JSON is reused directly, significantly reducing latency. A second LLM call is only made in the degraded path when Stage 1 fell back to the rule-based extractor.

---

## Startup Pre-warming

`app/main.py` lifespan fires a background thread on startup that calls `pipeline.icd_prediction_service.warm_up()`. This loads both MiniLM + FAISS and BioGPT into memory before the first request arrives, avoiding cold-start latency on the first analyze call.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health / version info |
| `GET` | `/review` | Interactive demo UI |
| `POST` | `/api/v1/analyze` | Run full pipeline |
| `GET` | `/api/v1/meta/review` | Pipeline configuration metadata |
| `GET` | `/api/v1/health` | Liveness check |

### POST /api/v1/analyze

**Request:**
```json
{
  "note_text": "Patient has uncontrolled diabetes with kidney damage. Denies chest pain.",
  "patient_id": "optional",
  "encounter_id": "optional",
  "include_report": true
}
```

**Response:**
```json
{
  "mode": "full | degraded",
  "entities": { "diseases": [], "symptoms": [], "severity": [], "negations": [], "complications": [] },
  "icd_codes": [ { "code": "E11.21", "description": "...", "confidence": 0.97 } ],
  "diagnosis": [ { "label": "...", "probability": 0.95, "rationale": "..." } ],
  "risks": [ { "label": "...", "severity": "high", "rationale": "..." } ],
  "report": "Subjective: ...\nObjective: ...\nAssessment: ...\nPlan: ...",
  "validation_notes": []
}
```

---

## Degraded Mode

Every stage has an independent fallback. The pipeline always returns a result.

| Stage | Primary | Fallback | Trigger |
|-------|---------|----------|---------|
| Understanding | `gemma4:31b-cloud` | Regex NLP extractor | Timeout, JSON parse error, model unavailable |
| ICD Prediction | FAISS + BioGPT | Catalog label lookup (20 entries) | FAISS index not built, model load failure |
| Report | Stage 1 `preliminary_report` / `gemma4:31b-cloud` | Template-based `DocumentationService` | Empty preliminary report |

`mode: "degraded"` is set in the response when any fallback activates. `validation_notes` lists the specific reason per stage.

---

## FAISS Index

**Build script:** `scripts/build_icd_index.py`  
**Source:** `Dataset/icd10orderfiles/icd10cm_codes_2026.txt` (74,719 codes)  
**Output:** `models/icd_index/index.faiss` + `models/icd_index/codes.json`  
**Embedding:** `all-MiniLM-L6-v2`, `batch_size=512`, `normalize_embeddings=True`  
**Index type:** `faiss.IndexFlatIP` (exact inner product = cosine on unit vectors)  

To rebuild after a dataset update:
```bash
python scripts/build_icd_index.py
```

---

## Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_MEDGEMMA` | `true` | Enable Stage 1 LLM |
| `ENABLE_ICD_MODEL` | `false` | BioBERT classifier (no weights, disabled) |
| `ENABLE_BIOGPT` | `true` | BioGPT re-ranker |
| `LLM_MODEL` | `gemma4:31b-cloud` | Ollama model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `ICD_INDEX_PATH` | `models/icd_index` | FAISS index directory |
| `ICD_RETRIEVER_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `ICD_RETRIEVAL_K` | `100` | Candidates passed to BioGPT |
| `ICD_TOP_K` | `5` | Final codes returned |

---

## Term Catalog

**File:** `app/services/catalog.py`

Central knowledge base for entity resolution, ICD mapping, and rule evaluation. Used by the fallback prediction service and rule engine combination rules. Entries have the shape:

```python
{
    "label":           "type 2 diabetes mellitus",
    "aliases":         ["diabetes", "dm2", "t2dm"],
    "entity_type":     "disease",
    "icd_code":        "E11.9",
    "icd_description": "Type 2 diabetes mellitus without complications",
    "diagnosis_label": "Type 2 diabetes mellitus",
}
```

Current catalog covers: hypertension, type 2 diabetes, CKD, pneumonia, asthma, COPD, heart failure, atrial fibrillation, UTI, coccyx injury, anxiety, depression, back pain, and common symptoms (chest pain, dyspnea, fever, nausea, headache, abdominal pain, edema, fatigue).

## Project Structure

```
app/
├── main.py                   FastAPI app, static mounts
├── api/
│   ├── router.py             API router aggregator
│   └── routes/
│       ├── analyze.py        POST /api/v1/analyze
│       ├── health.py         GET  /api/v1/health
│       └── meta.py           GET  /api/v1/meta/review
├── core/
│   └── config.py             Settings (env-driven)
├── domain/
│   └── schemas.py            Pydantic models
├── services/
│   ├── pipeline.py           Orchestrates all 4 stages
│   ├── understanding.py      Stage 1 — LLM entity extraction
│   ├── icd_prediction.py     Stage 2 — ICD Model ICD coding
│   ├── rules.py              Stage 3 — Combination rules
│   ├── reporting.py          Stage 4 — LLM report generation
│   ├── catalog.py            Term catalog, alias maps, combination rules
│   ├── extractor.py          Fallback regex NLP extractor
│   ├── diagnosis.py          Fallback diagnosis suggester
│   ├── risks.py              Fallback risk detector
│   └── documentation.py     Fallback report generator
└── static/
    ├── review.html           Demo UI
    ├── review.css
    └── review.js
models/
└── biobert/                  Local ICD Model weights (436 MB)
```

---

## Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL` | `gemma4:31b-cloud` | Ollama model tag for understanding + reporting |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base |
| `ICD_MODEL_NAME` | `models/icd10_prediction` | Path or HuggingFace ID for ICD Model |
| `ENABLE_MEDGEMMA` | `false` | Enable LLM understanding stage |
| `ENABLE_ICD_MODEL` | `false` | Enable ICD Model ICD stage |
| `ICD_TOP_K` | `5` | Max ICD candidates from ICD Model |

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| API framework | FastAPI 0.115+ |
| Runtime | Python 3.12, Uvicorn |
| LLM inference | Ollama (local HTTP) |
| LLM model | gemma4:31b-cloud |
| ICD encoder | ICD Model base cased v1.1 (HuggingFace Transformers) |
| ML runtime | PyTorch 2.x |
| Data validation | Pydantic v2 |
| Package management | pyproject.toml (PEP 517) |

- detect clinical risks
- generate structured medical documentation

For the hackathon MVP, the implementation must align with `Models.md`, `clinical_icd_prompt.md`, and `FIXES.md`.

## 2. Hackathon Architecture Decision

We use a modular monolith with a fixed stage order.

## 3. System Context

```text
Client or Demo UI
        |
        v
    FastAPI API
        |
        v
Structured Clinical Pipeline
  |- MedGemma Understanding
  |- ICD Model ICD Prediction
  |- Rule Engine Validation
  |- MedGemma Report Generation
        |
        v
 Structured JSON Response
```

## 4. Core Principles

- Models generate clinical knowledge.
- Rules enforce coding correctness.
- The orchestrator controls stage order.
- Fallbacks exist only for degraded mode.

## 5. Logical Components

### 5.1 API Layer

Responsibilities:

- receive clinical note text
- validate request schema
- trigger the pipeline
- return structured output

Initial endpoints:

- `GET /health`
- `POST /api/v1/analyze`

### 5.2 MedGemma Understanding Stage

Responsibilities:

- entity extraction
- negation handling
- diagnosis suggestion
- risk detection

### 5.3 ICD Model ICD Prediction Stage

Responsibilities:

- predict top ICD candidates
- remain separate from the rule engine
- be configurable through `ICD_MODEL_NAME`

### 5.4 Rule Engine

Responsibilities:

- validate ICD codes
- apply combination rules
- apply specificity and excludes logic
- emit final ICD codes only

### 5.5 MedGemma Report Stage

Responsibilities:

- generate the final structured report
- consume validated output only

## 6. Request and Response Contract

### Request

```json
{
  "patient_id": "optional-string",
  "encounter_id": "optional-string",
  "note_text": "free text clinical note",
  "include_report": true
}
```

### Response

```json
{
  "mode": "full",
  "entities": {
    "diseases": [],
    "symptoms": [],
    "severity": [],
    "negations": [],
    "complications": []
  },
  "icd_codes": [],
  "diagnosis": [],
  "risks": [],
  "report": "",
  "validation_notes": []
}
```

## 7. Internal Pipeline Flow

```text
note_text
  -> MedGemma understanding
  -> ICD Model ICD prediction
  -> rule validation
  -> MedGemma report generation
  -> response assembly
```

## 8. Suggested Repository Structure

```text
app/
  api/
    routes/
      analyze.py
      health.py
    router.py
  core/
    config.py
  domain/
    schemas.py
  services/
    understanding.py
    icd_prediction.py
    rules.py
    reporting.py
    pipeline.py
  main.py
tests/
docs/
```

## 9. Data Strategy

- keep a small in-code terminology catalog for fallback logic and rule coverage
- use de-identified or synthetic notes for demos and tests
- treat heuristics as degraded-mode implementations only

## 10. Delivery Phases

### MVP

- fixed four-stage orchestrator
- structured prompt-aligned response schema
- explicit degraded mode
- judge review surface

## 11. Deliberately Deferred

- full ICD-10 coverage
- billing-grade coding accuracy claims
- production security and PHI handling
- real-time hospital integration

## 12. Recommended Build Order

1. run MedGemma and ICD Model in full mode
2. expand ICD terminology and rules
3. benchmark model-backed stages against sample notes
4. add a stronger clinical review UI

## 13. What Success Looks Like

A demo user pastes a clinical note and immediately sees:

- structured entities
- final ICD-10 suggestions after rules
- likely diagnoses
- risk flags
- a concise structured report
- whether the system ran in `full` or `degraded` mode

That is enough for a strong hackathon story and gives us a clean base to extend after the event.
