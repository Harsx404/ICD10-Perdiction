# FIXES.md  
## Clinical Intelligence System – Alignment Fixes

---

# 🧠 Purpose

This document defines the **required fixes** to align the implementation with:
- MODELS.md (model ownership)
- clinical_icd_prompt.md (pipeline behavior)

---

# 🚨 Core Problem

Current system:
- Incorrect pipeline order
- Missing BioBERT ICD stage
- Overuse of deterministic logic
- Incorrect response schema
- MedGemma underutilized

---

# ✅ FIX 1: Enforce Pipeline Order

## Required Pipeline

```
Input Clinical Text
    ↓
[1] MedGemma (Understanding)
    ↓
[2] BioBERT (ICD Prediction)
    ↓
[3] Rule Engine (Validation)
    ↓
[4] MedGemma (Report Generation)
```

## Rules
- Do NOT skip any stage
- Do NOT reorder stages

---

# ✅ FIX 2: Use MedGemma as PRIMARY Model

## Stage 1 (Mandatory)
MedGemma must:
- Extract entities
- Detect negations
- Suggest diagnosis
- Detect risks

## Stage 4 (Mandatory)
MedGemma must:
- Generate final report

## ❌ Do NOT use MedGemma only as summary

---

# ✅ FIX 3: Add BioBERT ICD Stage

## Interface

```python
class IcdPredictionService:
    def predict(text: str) -> List[str]:
        pass
```

## Requirements
- Must return top candidate ICD codes
- Must be separate from rule engine
- Must be configurable via ICD_MODEL_NAME

## Temporary Fallback
- Retrieval-based ICD mapping allowed
- Still MUST follow this stage

---

# ✅ FIX 4: Restrict Rule Engine Responsibility

## Rule Engine SHOULD:
- Validate ICD codes
- Apply combination rules
- Apply excludes rules
- Enforce specificity

## Rule Engine SHOULD NOT:
- Extract entities
- Predict diseases
- Replace model reasoning

---

# ✅ FIX 5: Fix API Response Schema

## REQUIRED FORMAT

```json
{
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
  "report": ""
}
```

## Rules
- Remove `llm_summary`
- Keep ICD codes final (after rules)
- Keep entities structured

---

# ✅ FIX 6: Implement Degraded Mode

## Behavior

If any model fails:

- MedGemma fails → fallback NLP
- BioBERT fails → fallback ICD mapping

## Output MUST include:

```json
{
  "mode": "full" | "degraded"
}
```

---

# ✅ FIX 7: Central Orchestrator Service

## Responsibilities

- Execute pipeline in correct order
- Pass data between stages
- Handle failures
- Assemble final response

---

# 🧪 TEST REQUIREMENTS

System must pass:

1. Pipeline order test
2. Schema validation test
3. Negation test
4. ICD combination test
5. Degraded mode test

---

# 🎯 FINAL GOAL

Transform system into:

> Structured Clinical Intelligence Pipeline

NOT:
- Heuristic system
- LLM-only system

---

# 🧠 FINAL RULE

```
Models → Generate knowledge
Rules → Enforce correctness
Pipeline → Control flow
```
