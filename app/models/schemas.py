from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    input: str
    # TODO: add more fields as needed

class AnalyzeResponse(BaseModel):
    result: str
    # TODO: add more fields as needed
