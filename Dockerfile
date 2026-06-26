FROM python:3.11-slim

# no .pyc, unbuffered logs (clean container output)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app code only. .dockerignore keeps .env / .venv / tests / pdfs OUT of the image,
# so no secret is ever baked in (manual §8/§10). Secrets arrive at runtime via env.
COPY app/ ./app/

# drop root
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# /health must answer within 60s of start (manual §8). stdlib only — no curl in slim.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').getcode()==200 else 1)"

# bind 0.0.0.0 so judges can reach it; PORT overridable.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
