from fastapi import APIRouter

from app.services.billing import (
    CostEstimate,
    CostEstimateRequest,
    ClaimVerification,
    InsuranceClaim,
    estimate_costs,
    verify_claim,
)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


@router.post("/estimate", response_model=list[CostEstimate])
def estimate(payload: CostEstimateRequest) -> list[CostEstimate]:
    return estimate_costs(payload.icd_codes)


@router.post("/verify", response_model=ClaimVerification)
def verify(payload: InsuranceClaim) -> ClaimVerification:
    return verify_claim(payload)
