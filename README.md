# My API Service

## Setup

1. Clone the repo
2. Copy `.env.example` to `.env` and fill in your values:
   ```
   cp .env.example .env
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Run Locally

```bash
uvicorn app.main:app --reload --port 8000
```

Or with Docker:

```bash
docker build -t my-api .
docker run -p 8000:8000 my-api
```

## Endpoints

| Method | Path       | Description           |
|--------|------------|-----------------------|
| GET    | `/health`  | Health check          |
| POST   | `/analyze` | Main analysis endpoint|

## Sample Request

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"input": ""}'
```

## Sample Response

```json
{
  "result": ""
}
```

## Deploy to Render

See deployment steps in the project docs.
