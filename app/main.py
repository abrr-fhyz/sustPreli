"""QueueStorm Investigator — fintech support-copilot API.

Exception handlers enforce the spec's HTTP code map and guarantee the process
never crashes on bad input: validation errors -> 400, anything unexpected ->
a non-sensitive 500 (no stack/secret leakage).
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routes import analyze, diagnostics, health

log = logging.getLogger("queuestorm")

app = FastAPI(title="QueueStorm Investigator", version="1.0.0")

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(diagnostics.router)


@app.exception_handler(RequestValidationError)
async def on_validation_error(request: Request, exc: RequestValidationError):
    # Bad JSON / missing required / bad enum -> 400 (spec), not FastAPI's 422.
    return JSONResponse(status_code=400, content={"error": "malformed_request"})


@app.exception_handler(Exception)
async def on_unhandled(request: Request, exc: Exception):
    # Log full detail server-side; return nothing sensitive to the caller.
    log.exception("unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"error": "internal_error"})
