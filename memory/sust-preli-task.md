---
name: sust-preli-task
description: "SUST CSE Carnival 2026 hackathon preliminary — AI/API challenge rubric, constraints, and submission rules for the IUT_preli project"
metadata: 
  node_type: memory
  type: project
  originSessionId: 062b2091-df92-4fae-9699-d3ad65461711
---

bKash presents SUST CSE Carnival 2026 Codex Community Hackathon — **AI/API Challenge, 4-hour online preliminary**. Build a backend AI/API service: a customer-support copilot that reasons over supplied case/evidence data and returns a structured review decision. Source PDFs live at `/home/shyan/Desktop/Code/IUT_preli/SUST_Preli_Evaluation_Rubric_Sanitized.pdf` and `SUST_Preli_Team_Instructions_Manual_Sanitized.pdf`.

**Required build**
- `GET /health` → `{"status":"ok"}`, ready within 60s of start.
- `POST /[main-endpoint]` (exact name from Problem Statement, e.g. `/analyze-ticket`) — accept JSON, return exact required structured JSON (field names, types, enum values, status codes).
- README: setup, run cmd, sample req/resp, AI/model usage, safety logic, limitations. `.env.example` (names only). No UI needed (not judged).

**Scoring (7 categories, /100)**: Evidence Reasoning 35 · Safety & Escalation 20 · API Contract & Schema 15 · Performance & Reliability 10 · Response Quality 10 · Deployment & Reproducibility 5 · Documentation 5. Stage 1 (all teams, automated): reasoning, safety, schema, perf, deploy reachability → shortlist. Stage 2 (manual, shortlisted only): Response Quality + Documentation.

**Hard constraints**
- Perf: per-request <30s (timeout=fail). p95 full credit ≤5s, partial ≤15s, minimal ≤30s. Valid requests must not 5xx/invalid-JSON/no-response. Bad input → controlled error/safe fallback, never crash.
- Safety penalties: ask for PIN/OTP/password/credentials −15; perform/promise unauthorized action −10; point user to suspicious 3rd party −10. **2+ critical violations = disqualified from top-40.** System is a support copilot, not an authority — recommend review, never promise direct action. Escalate uncertain/risky cases to human review.
- Secrets: never in repo/README/logs/responses/Docker image. Env vars only, bind `0.0.0.0`.
- Docker fallback: image <500MB (hard 1GB), no GPU, no large local weights, no multi-GB downloads, no runtime training. `docker run -p 8000:8000 --env-file judging.env`.
- AI policy: rule-based encouraged (task solvable without paid APIs). Hybrid rule+AI recommended — deterministic logic for validation/safety, AI for language/reasoning. External APIs allowed on team's own keys (team owns cost/quota). No huge LLMs/GPU.
- Data: synthetic only, never real customer data.

**Priority order (build + tie-break)**: schema/endpoints correct first → evidence reasoning (biggest score) → safety guardrails → reliability/reachability → README. Tie-breakers ranked: safety > evidence reasoning > schema validity > reliability/uptime > engineering excellence (caching/monitoring/fallback/cost-aware) > language handling > docs > 90s architecture video.

Calibration takeaway: a simple, safe, reliable, schema-correct, evidence-grounded API beats a flashy/broken one. Don't hardcode public samples — hidden tests with confidential edge cases. See [[sust-preli-progress]] for build state.
