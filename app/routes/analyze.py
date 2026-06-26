from fastapi import APIRouter, HTTPException
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.logic import run_analysis
from app.utils.safety import safety_filter

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    # Safety check before processing
    if not safety_filter(request.input):
        raise HTTPException(status_code=400, detail="Input failed safety check.")

    result = run_analysis(request.input)
    return AnalyzeResponse(result=result)
