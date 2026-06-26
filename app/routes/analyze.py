from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse
)
from app.services.logic import run_analysis

router = APIRouter()


@router.post("/analyze-ticket", response_model=AnalyzeResponse)
def analyze_ticket(request: AnalyzeRequest) -> AnalyzeResponse:
    # 422: schema-valid but semantically empty complaint.
    if not request.complaint.strip():
        raise HTTPException(status_code=422, detail="complaint must not be empty")

    # Safety is enforced on OUTPUT fields (see Section 8), not by rejecting
    # input. Phishing/injection complaints must be processed, not 400'd:
    # the phishing path classifies them, and run_analysis never executes
    # instructions embedded in the complaint.
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
