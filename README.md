# DraftBridge

AI-powered architectural co-pilot that transforms hand-drawn sketches into professional 3D visualizations, compliance reports, and CAD/BIM export files.

Built with a Python FastAPI backend, Next.js 16 frontend, and deep integration with AWS services (S3, DynamoDB, Bedrock).

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [AWS Infrastructure](#aws-infrastructure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Frontend](#frontend)
- [Testing](#testing)
- [Deployment](#deployment)
- [Project Structure](#project-structure)

---

## Features

### Sketch Analysis
Upload a hand-drawn architectural sketch (JPEG, PNG, WEBP). The AI extracts text annotations, detects rooms, identifies architectural elements (walls, doors, windows, staircases), maps spatial relationships, and generates a human-readable descriptive summary — all via Amazon Nova Lite vision.

### Photorealistic 3D Rendering
Generate 1024x1024 photorealistic renders from sketch analysis data using Amazon Nova Canvas. Supports customizable style, materials, and lighting options.

### Design Refinement Chat
Multi-turn conversational interface powered by the Bedrock Converse API. Users describe changes ("make the kitchen larger", "add skylights"), and the AI maintains context across the conversation. When the user confirms they are done, all refinements are consolidated into a single coherent prompt for re-rendering.

### Refined Rendering
After chat refinement, a new render is generated using the consolidated prompt — incorporating all user-requested changes into a single coherent image.

### Walkthrough Video Generation
Generate 6-second, 24fps, 1280x720 walkthrough videos via Amazon Nova Reel. Uses async Bedrock invocation with polling. Chat refinements carry through to the video prompt automatically.

### Compliance Checking
Three AI-powered compliance analyses, each using Nova Lite with specialized prompts:
- **Building Code** — checks against IBC and other specified codes, returns violations with severity and remediation
- **ADA Accessibility** — validates doorway widths, ramp requirements, clearances, bathroom accessibility
- **Energy Efficiency** — analyzes window-to-wall ratio, insulation, HVAC layout, thermal bridging

### CAD/BIM Export
Export designs in three formats:
- **DXF** — full R2010 format via `ezdxf` with per-room layers, wall lines, dimension annotations, and element markers
- **IFC** — IFC2X3 STEP/SPF text output with project hierarchy (IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey), IfcSpace for rooms, and extruded wall geometry
- **OBJ** — Wavefront OBJ with extruded room boxes (floor, ceiling, 4 walls) grouped by room name

### Design Version Control
Snapshot design state at any point, retrieve full version history, and compare two versions with field-level diffs.

### Health Monitoring
Health endpoint checks connectivity to S3, DynamoDB, and Bedrock, returning per-service status.

---

## Architecture Overview

```
┌─────────────────┐         ┌──────────────────────────────────────────┐
│   Next.js 16    │  HTTP   │              FastAPI Backend              │
│   Frontend      │────────▶│                                          │
│   (Port 3000)   │         │  Routers → Agents → Services → AWS      │
└─────────────────┘         └──────────────────────────────────────────┘
                                          │         │         │
                                          ▼         ▼         ▼
                                     ┌────────┐ ┌───────┐ ┌────────┐
                                     │Bedrock │ │  S3   │ │DynamoDB│
                                     └────────┘ └───────┘ └────────┘
```

### Key Patterns

- **Dependency Injection** — AWS clients created once via `@lru_cache`, injected through FastAPI `Depends()`
- **Agent Pattern** — each AI capability is a class inheriting `BaseAgent`, which provides Bedrock invocation with exponential-backoff retry (3 attempts)
- **Single-Table DynamoDB** — all entities share one table with composite `PK` / `SK` keys
- **Synchronous Handlers** — all backend code is sync; FastAPI runs sync endpoints in a threadpool
- **Custom Exception Hierarchy** — `DraftBridgeError` base class with `status_code`, caught by global exception handlers
- **Presigned URLs** — S3 downloads served via temporary signed URLs (1-hour default expiry)

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.11+ |
| Framework | FastAPI + Uvicorn |
| Config | pydantic-settings (loads from `.env`) |
| Data Models | Pydantic v2 |
| AWS SDK | boto3 |
| CAD Export | ezdxf |
| Logging | Custom structured JSON logger |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | Next.js 16 (App Router) |
| Language | TypeScript (strict mode off, allowJs enabled) |
| Styling | Tailwind CSS 3 |
| AWS SDK | @aws-sdk/client-s3 |

### Testing
| Component | Technology |
|-----------|-----------|
| Framework | pytest + pytest-asyncio |
| Property-Based | hypothesis |
| AWS Mocking | moto (mock_aws) |
| HTTP Client | httpx AsyncClient + ASGITransport |

---

## AWS Infrastructure

### Amazon S3

Stores all binary assets with prefix-based organization:

| Prefix | Content |
|--------|---------|
| `sketches/` | Uploaded sketch images (JPEG/PNG/WEBP) |
| `renders/` | Generated 3D render images (PNG) |
| `videos/{design_id}/{video_id}/` | Walkthrough video files (MP4) |
| `exports/` | CAD/BIM export files (DXF/IFC/OBJ) |

The bucket is auto-created on startup if it doesn't exist. Files are accessed via presigned URLs with configurable expiry.

### Amazon DynamoDB

Single-table design with composite primary key (`PK` + `SK`), using PAY_PER_REQUEST billing:

| PK | SK Pattern | Entity |
|----|-----------|--------|
| `DESIGN#{id}` | `METADATA` | Design record (status, sketch key, analysis data) |
| `DESIGN#{id}` | `RENDER#{render_id}` | Render metadata (S3 key, prompt, style) |
| `DESIGN#{id}` | `VIDEO#{video_id}` | Video metadata (status, invocation ARN, S3 key) |
| `DESIGN#{id}` | `COMPLIANCE#{report_id}` | Compliance report (type, data, version) |
| `DESIGN#{id}` | `EXPORT#{export_id}` | Export metadata (format, S3 key, status) |
| `DESIGN#{id}` | `VERSION#{number}` | Version snapshot (analysis state, description) |
| `DESIGN#{id}` | `CHAT#{timestamp}#{msg_id}` | Chat messages (chronologically ordered) |

The table is auto-created on startup if it doesn't exist.

### Amazon Bedrock

Three foundation models are used:

| Model | ID | Purpose |
|-------|----|---------|
| Nova Lite | `amazon.nova-lite-v1:0` | Sketch analysis (vision), compliance checking, chat refinement, descriptive summaries |
| Nova Canvas | `amazon.nova-canvas-v1:0` | Photorealistic image generation (1024x1024) |
| Nova Reel | `amazon.nova-reel-v1:0` | Walkthrough video generation (1280x720, 6s, 24fps) |

Nova Lite and Nova Canvas use synchronous `invoke_model`. Nova Reel uses `start_async_invoke` with polling via `get_async_invoke`.

All Bedrock calls go through `BaseAgent.invoke_bedrock()` which provides retry with exponential backoff (3 attempts, handles `ThrottlingException` and `ServiceUnavailableException`).

The ChatAgent uses the Bedrock **Converse API** (`bedrock.converse()`) for multi-turn conversations with full message history.

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- AWS account with Bedrock model access enabled (Nova Lite, Nova Canvas, Nova Reel)
- Docker & Docker Compose (optional)

### Local Development

```bash
# Backend
cd final-updated
cp .env.example .env          # Edit with your AWS credentials
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd final-updated/frontend
npm install
npm run dev
```

Backend: `http://localhost:8000` · Frontend: `http://localhost:3000`

### Docker

```bash
cd final-updated
docker-compose up
```

Starts backend on port 8000 and frontend on port 3000.

---

## Environment Variables

```env
# App
APP_NAME=DraftBridge API
ENVIRONMENT=development
PORT=8000
LOG_LEVEL=info

# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Resources (auto-created on startup if missing)
S3_BUCKET_NAME=draftbridge-development-assets-YOUR_ACCOUNT_ID
DYNAMODB_TABLE_NAME=draftbridge-designs

# Bedrock Models
BEDROCK_TEXT_MODEL=amazon.nova-lite-v1:0
BEDROCK_IMAGE_MODEL=amazon.nova-canvas-v1:0
BEDROCK_VIDEO_MODEL=amazon.nova-reel-v1:0

# Limits
MAX_UPLOAD_SIZE_MB=10
PRESIGNED_URL_EXPIRY=3600
```

---

## API Reference

### Sketches

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sketches` | Upload sketch image (multipart form), returns analysis with rooms, elements, summary |
| `GET` | `/api/sketches/{sketch_id}` | Retrieve full design record including analysis data |

### Renders

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/renders` | Generate render from analysis or refined prompt |
| `GET` | `/api/renders/{render_id}` | Get render metadata and presigned image URL |

### Videos

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/videos` | Start async video generation (returns 202) |
| `GET` | `/api/videos/{video_id}` | Poll video status; returns URL when complete |

### Compliance

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/compliance/building-code` | Building code compliance check |
| `POST` | `/api/compliance/accessibility` | ADA accessibility validation |
| `POST` | `/api/compliance/energy` | Energy efficiency analysis |

### Exports

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/exports` | Generate CAD/BIM export (DXF, IFC, or OBJ) |
| `GET` | `/api/exports/{export_id}` | Get export metadata and presigned download URL |

### Versions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/versions/{design_id}` | Get version history |
| `GET` | `/api/versions/{design_id}/{version}` | Get specific version snapshot |
| `POST` | `/api/versions/{design_id}/compare` | Compare two versions (field-level diff) |

### Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat/{design_id}/messages` | Send message; returns assistant response + confirmation flag |
| `GET` | `/api/chat/{design_id}/messages` | Get full conversation history |

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Service health with S3, DynamoDB, Bedrock connectivity status |

---

## Frontend

### Pages

| Route | Description |
|-------|-------------|
| `/` | Landing page with hero, features, how-it-works, and CTA sections |
| `/upload` | Full workflow: upload → analyze → render → chat → refined render → video → export |

### Workflow

The upload page implements a guided 6-step workflow:

1. **Upload** — drag-and-drop or click to upload a sketch image
2. **Analysis** — AI analyzes the sketch, displays detected rooms and elements with a descriptive summary
3. **Render** — generates initial photorealistic 3D visualization via Nova Canvas
4. **Chat Refinement** — side-by-side render + chat panel for iterative design changes
5. **Refined Render** — generates updated render incorporating all chat refinements
6. **Video + Export** — generate walkthrough video and download CAD/BIM files (DXF/IFC/OBJ)

### Components

| Component | Description |
|-----------|-------------|
| `Header.tsx` | Sticky navigation with responsive mobile menu |
| `SketchUploader.tsx` | Main workflow orchestrator with stage tracking and progress indicator |
| `ChatPanel.tsx` | Multi-turn chat interface with message history and auto-scroll |
| `VideoStatusIndicator.tsx` | Polls video status with spinner, complete, and failed states |
| `VersionNavigator.js` | Version history browser |
| `VersionComparison.js` | Side-by-side version diff view |
| `SideBySideView.js` | Render comparison layout |
| `DifferenceHighlighter.js` | Visual diff highlighting |
| `versionService.js` | API client for version endpoints |

---

## Testing

```bash
cd final-updated
pytest                              # run all tests
pytest tests/test_agents/           # agent tests only
pytest tests/test_properties/       # property-based tests only
pytest tests/test_routers/          # router tests only
pytest tests/test_services/         # service tests only
```

### Test Coverage

| Directory | Tests |
|-----------|-------|
| `test_agents/` | ChatAgent (Converse API, confirmation detection, refined prompt building), SketchAgent (descriptive summary), VisualizationAgent (refined rendering) |
| `test_properties/` | Property-based tests for sketch-to-video pipeline (hypothesis) |
| `test_routers/` | Chat router integration tests |
| `test_services/` | DatabaseService chat message persistence |

All tests use `moto` for AWS mocking — no real AWS calls are made. Shared fixtures in `conftest.py` provide mock S3, DynamoDB, Bedrock clients, and an async test client with full dependency overrides.

---

## Deployment

### EC2 Deployment

The `deploy/` directory contains user-data scripts for automated EC2 provisioning:

- `userdata.sh` — template with placeholder credentials (replace before launch)
- `launch-userdata.sh` — ready-to-run script with injected credentials

Both scripts automate:
1. Install Docker, Node.js, Nginx on Amazon Linux
2. Clone the repository
3. Build and start the backend via Docker (port 8000)
4. Build and start the Next.js frontend (port 3000)
5. Configure Nginx as reverse proxy (port 80):
   - `/api/*` → backend (port 8000)
   - `/*` → frontend (port 3000)
   - `/health` → backend health check

### Docker Compose

```yaml
services:
  backend:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    volumes: [./app:/app/app]    # hot reload in dev

  frontend:
    build: ../frontend
    ports: ["3000:3000"]
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
    depends_on: [backend]
```

---

## Project Structure

```
final-updated/
├── app/
│   ├── main.py                 # FastAPI app, lifespan (auto-creates S3/DynamoDB), CORS, error handlers
│   ├── config.py               # Settings singleton via pydantic-settings
│   ├── dependencies.py         # Depends() factories for AWS clients, services, agents
│   ├── agents/
│   │   ├── base_agent.py       # Bedrock invoke with retry + async invoke for Nova Reel
│   │   ├── sketch_agent.py     # Text extraction + architecture analysis (Nova Lite vision)
│   │   ├── visualization_agent.py  # Renders (Nova Canvas) + Videos (Nova Reel)
│   │   ├── compliance_agent.py # Building code, ADA, energy analysis
│   │   ├── chat_agent.py       # Multi-turn chat via Converse API
│   │   └── export_agent.py     # DXF/IFC/OBJ file generation
│   ├── models/                 # Pydantic request/response models
│   │   ├── sketch.py           # SketchAnalysis, Room, ArchitecturalElement, TextBlock
│   │   ├── render.py           # RenderRequest, RenderResponse
│   │   ├── video.py            # VideoRequest, VideoResponse
│   │   ├── compliance.py       # ComplianceReport, AccessibilityReport, EnergyReport
│   │   ├── export.py           # ExportRequest, ExportResponse
│   │   ├── version.py          # DesignVersion, VersionDiff, VersionHistoryResponse
│   │   └── chat.py             # ChatMessage, ChatResponse, ChatHistoryResponse
│   ├── routers/                # FastAPI routers (one per resource, prefixed /api/)
│   │   ├── sketches.py         # POST/GET /api/sketches
│   │   ├── renders.py          # POST/GET /api/renders
│   │   ├── videos.py           # POST/GET /api/videos
│   │   ├── compliance.py       # POST /api/compliance/*
│   │   ├── exports.py          # POST/GET /api/exports
│   │   ├── versions.py         # GET/POST /api/versions
│   │   ├── chat.py             # POST/GET /api/chat
│   │   └── health.py           # GET /api/health
│   ├── services/
│   │   ├── storage_service.py  # S3 upload, download, presigned URLs, delete
│   │   ├── database_service.py # DynamoDB CRUD for all entity types
│   │   └── version_control_service.py  # Version snapshots and comparison
│   └── utils/
│       ├── errors.py           # DraftBridgeError, DesignNotFoundError, AWSServiceError, etc.
│       └── logging.py          # Structured JSON logger
├── tests/
│   ├── conftest.py             # Shared fixtures (mock S3, DynamoDB, Bedrock, async client)
│   ├── test_agents/            # Agent unit tests
│   ├── test_properties/        # Property-based tests (hypothesis)
│   ├── test_routers/           # Router integration tests
│   └── test_services/          # Service unit tests
├── frontend/
│   ├── app/                    # Next.js App Router pages
│   │   ├── layout.tsx          # Root layout with Header and footer
│   │   ├── page.tsx            # Landing page (hero, features, how-it-works, CTA)
│   │   └── upload/page.tsx     # Upload workflow page
│   └── src/
│       ├── components/         # React components
│       │   ├── Header.tsx
│       │   ├── SketchUploader.tsx
│       │   ├── ChatPanel.tsx
│       │   ├── VideoStatusIndicator.tsx
│       │   ├── VersionNavigator.js
│       │   ├── VersionComparison.js
│       │   ├── SideBySideView.js
│       │   └── DifferenceHighlighter.js
│       └── services/
│           └── versionService.js
├── deploy/
│   ├── userdata.sh             # EC2 user-data template (placeholder credentials)
│   └── launch-userdata.sh      # EC2 user-data with injected credentials
├── requirements.txt
├── Dockerfile                  # python:3.11-slim
├── docker-compose.yml
└── .env.example
```
