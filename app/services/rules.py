from app.domain.schemas import ClinicalUnderstandingResult, IcdCode, IcdPredictionCandidate
from app.services.catalog import ICD_COMBINATION_RULES, TERM_LOOKUP

# Leading words that mark a negation phrase — stripped before matching against
# ICD descriptions so e.g. "no acute exacerbation" → "acute exacerbation"
# → suppresses J44.1 "COPD with acute exacerbation".
_NEGATION_PREFIXES = (
    "negative for",
    "without",
    "denies",
    "denied",
    "absent",
    "not",
    "no",
)

# When a bare phrase is negated, also suppress ICD descriptions that contain
# any of its synonyms.  E.g. "without complication" → bare phrase "complication"
# → also suppresses codes containing "exacerbation" or "status asthmaticus".
_PHRASE_SYNONYMS: dict[str, list[str]] = {
    "hypertension": ["hypertension", "hypertensive"],
    "complication": ["complication", "exacerbation", "status asthmaticus", "with acute"],
    "exacerbation":  ["exacerbation", "status asthmaticus", "with acute", "complication"],
    "infection":     ["infection", "infectious", "sepsis", "bacteremia"],
    "fever":         ["fever", "febrile"],
    "pain":          ["pain", "painful"],
}


def _is_positive_match(phrase: str, description: str) -> bool:
    """Return True only when *phrase* appears in *description* as a positive finding.

    If any negation marker appears in the 50-character window immediately before
    the phrase the code already encodes *absence* of that condition and must NOT
    be suppressed.  This handles constructs like "without diagnosis of X" where
    "without" and "X" are not immediately adjacent.

    Examples:
      phrase="hypertension", desc="…without diagnosis of hypertension" → False  (keep R030)
      phrase="hypertensive", desc="Hypertensive heart disease…"        → True   (suppress I13xx)
      phrase="exacerbation",  desc="…with acute exacerbation"           → True   (suppress J44.1)
    """
    desc = description.lower()
    idx = desc.find(phrase)
    if idx == -1:
        return False
    # Look at the window before the phrase for any negation marker.
    window = desc[max(0, idx - 50): idx]
    for marker in ("without", "no ", "absent", "not ", "w/o"):
        if marker in window:
            return False
    return True


def _extract_negated_phrases(negation_labels: set[str]) -> list[str]:
    """Strip leading negation words, expand synonyms, return all suppression terms."""
    phrases: list[str] = []
    for neg in negation_labels:
        phrase = neg.lower().strip()
        for prefix in _NEGATION_PREFIXES:
            if phrase.startswith(prefix + " "):
                phrase = phrase[len(prefix):].strip()
                break
        if len(phrase) <= 4:
            continue
        # Add the bare phrase plus all known synonyms.
        expanded = _PHRASE_SYNONYMS.get(phrase, [phrase])
        phrases.extend(expanded)
    return list(dict.fromkeys(phrases))  # deduplicate, preserve order


class RuleEngineService:
    def validate(
        self,
        understanding: ClinicalUnderstandingResult,
        candidates: list[IcdPredictionCandidate],
    ) -> tuple[list[IcdCode], list[str]]:
        notes: list[str] = []
        disease_labels = set(understanding.entities.diseases)
        negation_labels = set(understanding.entities.negations)
        complication_labels = set(understanding.entities.complications)

        if negation_labels:
            notes.append("Negated findings were excluded from ICD suggestion output.")

        deduped: dict[str, IcdCode] = {}
        for candidate in candidates:
            if candidate.evidence and set(candidate.evidence).issubset(negation_labels):
                continue
            existing = deduped.get(candidate.code)
            normalized = IcdCode(
                code=candidate.code,
                description=candidate.description,
                confidence=candidate.confidence,
            )
            if existing is None or normalized.confidence > existing.confidence:
                deduped[candidate.code] = normalized

        validated = list(deduped.values())

        # Suppress any code whose ICD description contains a negated phrase as a
        # *positive* finding.  Codes that already encode absence of the term
        # (e.g. R030 "…without diagnosis of hypertension") must NOT be suppressed —
        # they are exactly correct when the condition is negated.
        negated_phrases = _extract_negated_phrases(negation_labels)
        if negated_phrases:
            suppressed: list[str] = []
            kept: list[IcdCode] = []
            for code in validated:
                if any(_is_positive_match(phrase, code.description) for phrase in negated_phrases):
                    suppressed.append(code.code)
                else:
                    kept.append(code)
            if suppressed:
                validated = kept
                notes.append(
                    f"Codes suppressed due to negated clinical findings: {', '.join(suppressed)}"
                )

        if disease_labels:
            allowed_codes = {
                TERM_LOOKUP[label]["icd_code"]
                for label in disease_labels
                if label in TERM_LOOKUP and "icd_code" in TERM_LOOKUP[label]
            }
            if allowed_codes:
                # Prioritise disease-matched codes rather than hard-filtering,
                # so that symptom/complication codes can fill remaining slots
                # when fewer than 3 disease codes are available.
                validated.sort(
                    key=lambda c: (0 if c.code in allowed_codes else 1, -c.confidence)
                )

        for rule in ICD_COMBINATION_RULES:
            if (
                rule["if_disease"] in disease_labels
                and (
                    rule["if_complication"] in complication_labels
                    or rule["if_complication"] in disease_labels
                )
            ):
                validated = [
                    candidate for candidate in validated if candidate.code not in set(rule["remove_codes"])
                ]
                validated.append(
                    IcdCode(
                        code=rule["code"],
                        description=rule["description"],
                        confidence=0.97,
                    )
                )
                notes.append(rule["note"])

        deduped_final = {candidate.code: candidate for candidate in validated}
        validated = list(deduped_final.values())
        validated.sort(key=lambda candidate: candidate.confidence, reverse=True)
        return validated[:3], notes
