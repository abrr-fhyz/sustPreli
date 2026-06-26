from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse
)
from app.services.logic import run_analysis
from app.utils.safety import safety_filter

router = APIRouter()


@router.post(
    "/analyze-ticket",
    response_model=AnalyzeResponse
)
def analyze_ticket(request: AnalyzeRequest):

    # Semantic validation
    if not request.complaint.strip():
        raise HTTPException(
            status_code=422,
            detail="Complaint cannot be empty."
        )

    # Safety check
    if not safety_filter(request.complaint):
        raise HTTPException(
            status_code=400,
            detail="Input failed safety check."
        )

    try:
        result = run_analysis(request)

        # run_analysis should return a dict matching
        # AnalyzeResponse schema
        return AnalyzeResponse(**result)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )