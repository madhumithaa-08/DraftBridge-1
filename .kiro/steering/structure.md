# Project Structure

All application code lives under `final-updated/`.

```
final-updated/
├── app/                        # FastAPI backend
│   ├── main.py                 # App entry point, lifespan, CORS, error handlers
│   ├── config.py               # Settings singleton via pydantic-settings
│   ├── dependencies.py         # FastAPI Depends factories for AWS clients & services
│   ├── agents/                 # AI agent classes (Bedrock invocation logic)
│   │   ├── base_agent.py       # Shared retry/invoke logic; all agents inherit this
│   │   ├── sketch_agent.py     # Sketch analysis (Textract + Claude)
│   │   ├── visualization_agent.py  # Renders (Nova Canvas) + Videos (Nova Reel)
│   │   ├── compliance_agent.py # Building code, ADA, energy checks
│   │   └── export_agent.py     # CAD/BIM file generation
│   ├── models/                 # Pydantic request/response models (one file per domain)
│   ├── routers/                # FastAPI routers (one file per resource, prefixed /api/)
│   ├── services/               # Data layer: S3, DynamoDB, version control
│   └── utils/                  # errors.py (custom exceptions), logging.py (JSON logger)
├── tests/                      # pytest suite, mirrors app/ layout
│   ├── conftest.py             # Shared fixtures: mock_s3, mock_dynamodb, test_client
│   ├── test_agents/
│   ├── test_properties/        # Property-based (hypothesis) tests
│   ├── test_routers/
│   └── test_services/
├── frontend/                   # Next.js App Router frontend
│   ├── app/                    # Route pages (layout.tsx, page.tsx, upload/)
│   └── src/
│       ├── components/         # React components (Header, SketchUploader, etc.)
│       └── services/           # API client helpers
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Architecture Patterns

- Dependency injection via FastAPI `Depends()` — AWS clients are created once (`@lru_cache`) and injected into services and agents.
- Single-table DynamoDB design — all entities share one table with `PK` (e.g. `DESIGN#<id>`) and `SK` (e.g. `METADATA`, `RENDER#<id>`, `VERSION#<n>`).
- Agent pattern — each AI capability is a class inheriting `BaseAgent`, which provides Bedrock invocation with retry. Agents receive storage and database services via constructor injection.
- Custom exception hierarchy — `DraftBridgeError` base class with `status_code`; caught by global FastAPI exception handlers in `main.py`.
- Routers are thin — they validate input, call agents/services, and return Pydantic models. Business logic lives in agents and services.
- All backend code is synchronous — FastAPI runs sync handlers in a threadpool.
