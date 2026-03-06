# Tech Stack

## Backend (Python)

- Runtime: Python 3.11+
- Framework: FastAPI (with uvicorn)
- Config: pydantic-settings (loads from `.env`)
- AWS SDK: boto3
- Data models: Pydantic v2
- CAD export: ezdxf
- Logging: Custom structured JSON logger (`app/utils/logging.py`)

## Frontend (TypeScript/JavaScript)

- Framework: Next.js 16 (App Router)
- Language: TypeScript (strict mode off, allowJs enabled)
- Styling: Tailwind CSS 3
- Path alias: `@/*` maps to project root
- Some components are `.js`/`.css` (legacy), new components should be `.tsx`

## AWS Services

- S3: File storage (sketches, renders, videos, exports)
- DynamoDB: Design metadata (single-table design, PK/SK composite key)
- Bedrock: AI model invocation (Claude 3 Sonnet, Nova Canvas, Nova Reel)
- Textract: OCR for sketch text annotations

## Testing

- Framework: pytest + pytest-asyncio
- Property-based testing: hypothesis
- AWS mocking: moto (mock_aws context manager)
- HTTP test client: httpx AsyncClient with ASGITransport
- Test directory mirrors `app/` structure under `tests/`

## Containerization

- Backend Dockerfile: python:3.11-slim
- docker-compose: backend (port 8000) + frontend (port 3000)

## Common Commands

```bash
# Backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest                          # run all tests
pytest tests/test_services/     # run a specific test directory

# Frontend
cd final-updated/frontend
npm install
npm run dev                     # dev server on port 3000
npm run build                   # production build

# Docker
docker-compose up               # start both services
```
