from app.domain.schemas import DiagnosisSuggestion, ExtractedEntity
from app.services.catalog import TERM_LOOKUP


class DiagnosisService:
    def suggest(self, entities: list[ExtractedEntity]) -> list[DiagnosisSuggestion]:
        suggestions: list[DiagnosisSuggestion] = []

        for entity in entities:
            if entity.negated or entity.entity_type != "disease":
                continue

            concept = TERM_LOOKUP.get(entity.label)
            if not concept:
                continue

            suggestions.append(
                DiagnosisSuggestion(
                    label=concept["diagnosis_label"],
                    probability=min(entity.confidence + 0.04, 0.96),
                    rationale=f"Supported by note mention '{entity.mention}' during the understanding stage.",
                )
            )

        suggestions.sort(key=lambda item: item.probability, reverse=True)
        return suggestions[:5]
