# MODELS.md

## Clinical Intelligence System – Model Architecture

---

# 🧠 Overview

This system uses a hybrid multi-model architecture to ensure:

- High accuracy (ICD coding)
- Clinical reasoning (diagnosis + risk)
- Structured output (documentation)

---

# 🏗️ Model Stack

## 1. Clinical Understanding Model

Model: MedGemma 1.5Role:

- Clinical text understanding
- Entity extraction
- Diagnosis suggestion
- Risk detection
- Report generation

---

## Input

{
  "clinical_text": "Patient has uncontrolled diabetes with kidney damage"
}

## Output

{
  "diseases": ["type 2 diabetes"],
  "complications": ["nephropathy"],
  "severity": ["uncontrolled"]
}

---

## Prompt Template

You are a clinical AI assistant.
Extract structured medical information.
Return JSON only.

---

## 2. ICD Prediction Model

Model: BioBERT / Bio-LM
Task: Multi-label classification

Input:
{
  "text": "type 2 diabetes with nephropathy"
}

Output:
{
  "predicted_codes": ["E11.21"]
}

---

## 3. Rule Engine

Type: Rule-based (Python)

Role:

- Validate ICD codes
- Apply ICD rules

Example:
if diabetes + nephropathy:
    return E11.21

---

## 4. Documentation Model

Model: MedGemma 1.5

Role:

- Generate reports
- Summaries

---

# 🔗 Flow

Clinical Text → MedGemma → BioBERT → Rule Engine → MedGemma

---

# ⚠️ Principles

- Do not use LLM for final ICD codes
- Always validate with rules
- Use structured outputs

---

# ✅ Summary

Understanding → MedGemma
Prediction → BioBERT
Validation → Rules
Documentation → MedGemma
