"""Billing service — cost estimation & claim verification logic."""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel, Field

from app.services.catalog import ICD_CODE_TO_DESCRIPTION

log = logging.getLogger(__name__)

# ── Cost estimation models ────────────────────────────────────────────────────

class CostEstimate(BaseModel):
    code: str
    description: str
    estimated_cost_low: float
    estimated_cost_high: float
    drg_category: str


class CostEstimateRequest(BaseModel):
    icd_codes: list[str]


# Rough DRG-category lookup based on ICD chapter letter prefix.
_DRG_CATEGORIES: dict[str, tuple[str, float, float]] = {
    "A": ("Infectious Disease", 4000, 12000),
    "B": ("Infectious Disease", 4000, 12000),
    "C": ("Neoplasms", 8000, 45000),
    "D": ("Blood/Immune Disorders", 3000, 10000),
    "E": ("Endocrine/Metabolic", 3000, 9000),
    "F": ("Mental/Behavioral", 2000, 8000),
    "G": ("Nervous System", 5000, 20000),
    "H": ("Eye/Ear", 2000, 7000),
    "I": ("Circulatory System", 5000, 25000),
    "J": ("Respiratory System", 4000, 15000),
    "K": ("Digestive System", 4000, 18000),
    "L": ("Skin/Subcutaneous", 2000, 8000),
    "M": ("Musculoskeletal", 4000, 15000),
    "N": ("Genitourinary", 3000, 12000),
    "O": ("Pregnancy/Childbirth", 5000, 20000),
    "P": ("Perinatal", 6000, 30000),
    "Q": ("Congenital", 5000, 25000),
    "R": ("Symptoms/Signs", 2000, 6000),
    "S": ("Injury", 3000, 15000),
    "T": ("Injury/Poisoning", 3000, 15000),
    "V": ("External Causes", 1000, 5000),
    "W": ("External Causes", 1000, 5000),
    "X": ("External Causes", 1000, 5000),
    "Y": ("External Causes", 1000, 5000),
    "Z": ("Health Services/Factors", 500, 3000),
}

DEFAULT_DRG = ("General", 2000, 8000)


def estimate_costs(icd_codes: list[str]) -> list[CostEstimate]:
    results = []
    for code in icd_codes:
        clean = code.strip().upper().replace(".", "")
        prefix = clean[0] if clean else ""
        category, low, high = _DRG_CATEGORIES.get(prefix, DEFAULT_DRG)
        desc = ICD_CODE_TO_DESCRIPTION.get(clean, "Unknown code")
        results.append(CostEstimate(
            code=code,
            description=desc,
            estimated_cost_low=low,
            estimated_cost_high=high,
            drg_category=category,
        ))
    return results


# ── Claim verification models ────────────────────────────────────────────────

class ClaimIssue(BaseModel):
    code: str
    severity: str  # "info" | "warning" | "error"
    message: str


class ClaimVerification(BaseModel):
    status: str  # "approved" | "flagged" | "denied"
    issues: list[ClaimIssue] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class InsuranceClaim(BaseModel):
    icd_codes: list[str] = Field(default_factory=list)
    cpt_codes: list[str] = Field(default_factory=list)
    date_of_service: str = ""
    place_of_service: str = ""
    total_charge: float = 0
    authorization_number: str | None = None
    # Nested objects are accepted but not validated in detail
    patient: dict = Field(default_factory=dict)
    insurance: dict = Field(default_factory=dict)
    provider: dict = Field(default_factory=dict)


def verify_claim(claim: InsuranceClaim) -> ClaimVerification:
    issues: list[ClaimIssue] = []
    recommendations: list[str] = []

    # Basic validation rules
    if not claim.icd_codes:
        issues.append(ClaimIssue(
            code="ICD_MISSING",
            severity="error",
            message="No ICD-10 codes provided. At least one diagnosis code is required.",
        ))

    if not claim.cpt_codes:
        issues.append(ClaimIssue(
            code="CPT_MISSING",
            severity="warning",
            message="No CPT procedure codes provided. Claims typically require procedure codes.",
        ))
        recommendations.append("Add CPT codes corresponding to services rendered.")

    if not claim.date_of_service:
        issues.append(ClaimIssue(
            code="DOS_MISSING",
            severity="error",
            message="Date of service is required.",
        ))

    if claim.total_charge <= 0:
        issues.append(ClaimIssue(
            code="CHARGE_INVALID",
            severity="warning",
            message="Total charge should be greater than zero.",
        ))

    # Check ICD codes are valid format
    for code in claim.icd_codes:
        if not re.match(r"^[A-Z]\d{2,6}$", code.replace(".", "").upper()):
            issues.append(ClaimIssue(
                code="ICD_FORMAT",
                severity="warning",
                message=f"ICD code '{code}' may have an invalid format.",
            ))

    # Check provider NPI
    provider_npi = claim.provider.get("npi", "")
    if provider_npi and len(provider_npi) != 10:
        issues.append(ClaimIssue(
            code="NPI_FORMAT",
            severity="warning",
            message="Provider NPI should be exactly 10 digits.",
        ))

    # Check insurance info
    if not claim.insurance.get("member_id"):
        issues.append(ClaimIssue(
            code="MEMBER_ID_MISSING",
            severity="error",
            message="Insurance member ID is required.",
        ))

    # Determine status
    has_errors = any(i.severity == "error" for i in issues)
    has_warnings = any(i.severity == "warning" for i in issues)

    if has_errors:
        status = "denied"
    elif has_warnings:
        status = "flagged"
        recommendations.append("Review flagged items before submitting to payer.")
    else:
        status = "approved"
        recommendations.append("Claim appears complete. Ready for submission.")

    return ClaimVerification(
        status=status,
        issues=issues,
        recommendations=recommendations,
    )
