from app.domain.schemas import FinalClinicalContext


class DocumentationService:
    def generate(self, context: FinalClinicalContext) -> str:
        diagnosis_labels = [diagnosis.label for diagnosis in context.diagnosis]
        code_labels = [code.code for code in context.icd_codes]
        risk_labels = [risk.label for risk in context.risks]
        entities = context.entities
        positive_mentions = entities.diseases + entities.symptoms + entities.complications
        negated_mentions = entities.negations

        sections = [
            "Subjective: " + (", ".join(positive_mentions) if positive_mentions else "No positive findings extracted."),
            "Objective: Automated extraction completed with negation handling."
            + (f" Negated findings: {', '.join(negated_mentions)}." if negated_mentions else ""),
            "Assessment: " + (", ".join(diagnosis_labels) if diagnosis_labels else "No high-confidence diagnosis suggestion."),
            "Plan: Review ICD-10 suggestions "
            + (", ".join(code_labels) if code_labels else "none")
            + "."
            + (f" Monitor risks: {', '.join(risk_labels)}." if risk_labels else ""),
        ]
        return " ".join(sections)
