from __future__ import annotations

import re

from app.domain.schemas import ExtractedEntity
from app.services.catalog import NEGATION_TERMS, TERM_CATALOG


class ClinicalNlpService:
    def extract(self, note_text: str) -> list[ExtractedEntity]:
        entities: list[ExtractedEntity] = []
        seen: set[tuple[str, bool]] = set()

        for item in TERM_CATALOG:
            for alias in item["aliases"]:
                pattern = re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE)
                for match in pattern.finditer(note_text):
                    context = note_text[max(0, match.start() - 40):match.start()].lower()
                    negated = self._is_negated(context)
                    key = (item["label"], negated)
                    if key in seen:
                        continue

                    entities.append(
                        ExtractedEntity(
                            label=item["label"],
                            entity_type=item["entity_type"],
                            mention=match.group(0),
                            negated=negated,
                            confidence=0.92 if item["entity_type"] == "disease" else 0.82,
                            start=match.start(),
                            end=match.end(),
                        )
                    )
                    seen.add(key)

        entities.sort(key=lambda entity: (entity.start or 0, entity.label))
        return entities

    def _is_negated(self, context: str) -> bool:
        # Limit negation checks to the local context immediately before the mention.
        tail = context[-40:]
        return any(term in tail for term in NEGATION_TERMS)
