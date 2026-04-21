# Model Setup

## Required Model Stack

The realigned pipeline uses two model-backed stages:

- MedGemma understanding and report generation: `MedAIBase/MedGemma1.5:4b`
- ICD prediction: `AkshatSurolia/ICD-10-Code-Prediction`

If one of these stages is unavailable, the app drops to `degraded` mode and uses explicit fallbacks.

## 1. Install Ollama

Download Ollama from:

`https://ollama.com/download`

## 2. Pull MedGemma

```bash
ollama pull MedAIBase/MedGemma1.5:4b
```

Verify:

```bash
ollama run MedAIBase/MedGemma1.5:4b
```

## 3. Install ICD Model Runtime Dependencies

```bash
pip install "transformers>=4.40,<5.0" "torch>=2.2,<3.0" "huggingface_hub>=0.23,<1.0"
```

## 4. Download ICD Model

```bash
huggingface-cli download AkshatSurolia/ICD-10-Code-Prediction --local-dir models/icd10_prediction
```

Set:

```text
ICD_MODEL_NAME=AkshatSurolia/ICD-10-Code-Prediction
```

## 5. Run In Full Mode

PowerShell:

```powershell
$env:ENABLE_MEDGEMMA="true"
$env:ENABLE_ICD_MODEL="true"
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:LLM_MODEL="MedAIBase/MedGemma1.5:4b"
$env:ICD_MODEL_NAME="AkshatSurolia/ICD-10-Code-Prediction"
uvicorn app.main:app --reload
```

## 6. Review Surface

- `http://127.0.0.1:8000/review`
- `http://127.0.0.1:8000/docs`

## Degraded Mode

If MedGemma or the ICD stage is disabled or unavailable:

- the API still responds
- `mode` becomes `degraded`
- fallback behavior is recorded in `validation_notes`
