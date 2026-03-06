# DraftBridge v2

AI-powered architectural co-pilot that transforms hand-drawn sketches into professional 3D visualizations, compliance reports, and CAD/BIM files. Built as a single Python FastAPI backend with a Next.js frontend.

## Prerequisites

- **Python 3.11+**
- **AWS account** with credentials configured
- **Node.js 18+** (for the frontend)
- **Docker & Docker Compose** (optional, for containerized setup)

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd draftbridge-v2
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your AWS credentials and resource names:

```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=draftbridge-assets
DYNAMODB_TABLE_NAME=draftbridge-designs
```

### 3. Run with Python (development)

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

### 4. Run with Docker

```bash
docker-compose up
```

This starts both the backend (port 8000) and frontend (port 3000).

## AWS Setup

DraftBridge requires the following AWS resources:

### S3 Bucket

Create an S3 bucket for storing sketches, renders, videos, and export files. The bucket uses prefix-based organization:

- `sketches/` — Uploaded sketch images
- `renders/` — Generated 3D render images
- `videos/` — Walkthrough video files
- `exports/` — CAD/BIM export files

```bash
aws s3 mb s3://draftbridge-assets
```

### DynamoDB Table

Create a DynamoDB table with a composite primary key for storing all design metadata:

```bash
aws dynamodb create-table \
  --table-name draftbridge-designs \
  --key-schema \
    AttributeName=PK,KeyType=HASH \
    AttributeName=SK,KeyType=RANGE \
  --attribute-definitions \
    AttributeName=PK,AttributeType=S \
    AttributeName=SK,AttributeType=S \
    AttributeName=user_id,AttributeType=S \
    AttributeName=created_at,AttributeType=S \
  --global-secondary-indexes \
    'IndexName=user-index,KeySchema=[{AttributeName=user_id,KeyType=HASH},{AttributeName=created_at,KeyType=RANGE}],Projection={ProjectionType=ALL}' \
  --billing-mode PAY_PER_REQUEST
```

### Amazon Bedrock Model Access

Enable access to the following models in the AWS Bedrock console:

- **Anthropic Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`) — Sketch analysis and compliance checking
- **Amazon Nova Canvas** (`amazon.nova-canvas-v1:0`) — Photorealistic render generation
- **Amazon Nova Reel** (`amazon.nova-reel-v1:0`) — Walkthrough video generation

Amazon Textract is also used for extracting text annotations from sketches (no model access setup required).

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sketches` | Upload and analyze a sketch |
| `GET` | `/api/sketches/{sketch_id}` | Get sketch analysis results |
| `POST` | `/api/renders` | Generate a photorealistic render |
| `GET` | `/api/renders/{render_id}` | Get render status and URL |
| `POST` | `/api/videos` | Start walkthrough video generation |
| `GET` | `/api/videos/{video_id}` | Get video status and URL |
| `POST` | `/api/compliance/building-code` | Run building code compliance check |
| `POST` | `/api/compliance/accessibility` | Run ADA accessibility validation |
| `POST` | `/api/compliance/energy` | Run energy efficiency analysis |
| `POST` | `/api/exports` | Generate CAD/BIM export |
| `GET` | `/api/exports/{export_id}` | Get export status and download URL |
| `GET` | `/api/versions/{design_id}` | Get version history |
| `GET` | `/api/versions/{design_id}/{version}` | Get specific version |
| `POST` | `/api/versions/{design_id}/compare` | Compare two versions |
| `GET` | `/api/health` | Health check |

## Project Structure

```
draftbridge-v2/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py             # Settings via pydantic-settings
│   ├── dependencies.py       # AWS client dependency injection
│   ├── agents/
│   │   ├── base_agent.py     # Shared Bedrock invocation logic
│   │   ├── sketch_agent.py   # Sketch analysis (Textract + Bedrock)
│   │   ├── visualization_agent.py  # Renders (Nova Canvas) + Videos (Nova Reel)
│   │   ├── compliance_agent.py     # Building code, ADA, energy analysis
│   │   └── export_agent.py   # CAD/BIM file generation
│   ├── services/
│   │   ├── storage_service.py       # S3 operations
│   │   ├── database_service.py      # DynamoDB operations
│   │   └── version_control_service.py  # Design versioning
│   ├── routers/
│   │   ├── sketches.py       # POST/GET /api/sketches
│   │   ├── renders.py        # POST/GET /api/renders
│   │   ├── videos.py         # POST/GET /api/videos
│   │   ├── compliance.py     # POST /api/compliance/*
│   │   ├── exports.py        # POST/GET /api/exports
│   │   ├── versions.py       # GET/POST /api/versions
│   │   └── health.py         # GET /api/health
│   ├── models/               # Pydantic request/response models
│   └── utils/
│       ├── errors.py         # Custom exception classes
│       └── logging.py        # Structured JSON logging
├── tests/                    # pytest + hypothesis test suite
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```
