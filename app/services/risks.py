from app.domain.schemas import ExtractedEntity, RiskSignal
from app.services.catalog import RISK_RULES


class RiskDetectionService:
    def detect(self, entities: list[ExtractedEntity]) -> list[RiskSignal]:
        positive_labels = {entity.label for entity in entities if not entity.negated}
        risks: list[RiskSignal] = []

        for rule in RISK_RULES:
            if_all = set(rule.get("if_all", []))
            if_any = set(rule.get("if_any", []))

            if if_all and not if_all.issubset(positive_labels):
                continue
            if if_any and positive_labels.isdisjoint(if_any):
                continue

            risks.append(
                RiskSignal(
                    label=rule["label"],
                    severity=rule["severity"],
                    rationale=rule["rationale"],
                )
            )

        return risks

