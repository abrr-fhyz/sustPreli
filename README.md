# QueueStorm Investigator

Fintech support-copilot API. Reads complaint + `transaction_history`, decides what
true (complaint may contradict data), routes + replies safely. SUST Carnival 2026 preli.

Not classifier — investigator. Verdict grounded in transaction evidence, not just text.

## Stack

FastAPI + Pydantic. Stateless. No database (synthetic data arrives per request).
Engine seam (`app/services/engine.py`) currently safe default — heuristics plug in next.

## Run

Local:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Docker:
```bash
docker build -t queuestorm .
docker run -p 8000:8000 queuestorm
```

Tests:
```bash
pip install -r requirements-dev.txt
pytest -q
```

Smoke (server must run):
```bash
python smoke.py          # localhost
python smoke.py online   # REMOTE_URL in smoke.py
```

## Endpoints

- `GET /health` → `{"status":"ok"}`. Ready ≤60s after start.
- `POST /analyze-ticket` → JSON in/out, responds ≤30s.

HTTP codes:
- `200` ok
- `400` malformed — bad JSON / missing required field / bad enum
- `422` schema-valid but empty complaint
- `500` internal — non-sensitive body `{"error":"internal_error"}`, no stack/secret leak

Process never crashes on bad input. Every input → response.

## Sample

Request:
```json
{
  "ticket_id": "T1",
  "complaint": "amar taka transfer hoy nai kintu kete nise",
  "transaction_history": [
    {"transaction_id":"TX1","timestamp":"2026-01-01T10:00:00Z","type":"transfer","amount":500,"counterparty":"01700000000","status":"failed"}
  ]
}
```

Response: see `samples/sample_output.json`.

## Safety logic

Two layers:
1. Engine produces verdict + reply.
2. `scrub_response()` net runs on outgoing response before send — last guard even if
   engine/LLM emits unsafe text.

Net catches (rubric penalties):
- credential ask (PIN/OTP/password/card) → −15. Detect = request-verb near credential token.
- unauthorized money promise (refund/reverse/unblock without authority) → −10. Replace with
  "any eligible amount will be returned through official channels".
- suspicious 3rd-party referral (WhatsApp/Telegram/short links) → −10.

Violation found → swap field for safe canned string. Safe text passes unchanged.
Prompt-injection in complaint ignored — engine never executes complaint instructions.

When unsure → `evidence_verdict=insufficient_data` + `human_review_required=true`. Never guess.

## MODELS

No LLM wired yet. Engine = deterministic safe default. Architecture TBD (rule-based /
hybrid / LLM). Outbound allowed: OpenAI / Anthropic / HF / Cohere / Google. If hybrid
chosen later → `GEMINI_API_KEY` (names in `.env.example`, never committed).

## Limitations

- Reasoning engine = placeholder. Returns insufficient_data + escalate until heuristics added.
- Safety net = regex proximity, not primary guard; engine intended primary. Bare
  "your OTP is needed" (no request verb) may slip — covered by escalate-when-unsure default.
- Timestamps stored as string, compared not parsed.

## Deploy

Both paths supported:
- Live URL: Render (Dockerfile-based, `$PORT` honored).
- Docker image: `<5GB`, slim base.

No real data. No committed secrets (`.env` gitignored).
