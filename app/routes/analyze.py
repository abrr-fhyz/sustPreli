from fastapi import APIRouter, HTTPException

from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.engine import investigate
from app.utils.safety import scrub_response

router = APIRouter()


@router.post("/analyze-ticket", response_model=AnalyzeResponse)
def analyze_ticket(request: AnalyzeRequest) -> AnalyzeResponse:
    # 422: schema-valid but semantically empty complaint.
    if not request.complaint.strip():
        raise HTTPException(status_code=422, detail="complaint must not be empty")

    # Engine errors bubble to the app-level handler -> safe 500 (no crash).
    result = investigate(request)
    # Last-line safety net on whatever the engine produced.
    return scrub_response(result)