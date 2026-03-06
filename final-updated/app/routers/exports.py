from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.agents.export_agent import ExportAgent
from app.dependencies import get_export_agent, get_storage_service, get_database_service
from app.models.export import ExportRequest, ExportResponse
from app.models.sketch import SketchAnalysis
from app.services.database_service import DatabaseService
from app.services.storage_service import StorageService
from app.utils.errors import DesignNotFoundError
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.post("", response_model=ExportResponse)
async def create_export(
    request: ExportRequest,
    export_agent: ExportAgent = Depends(get_export_agent),
    db: DatabaseService = Depends(get_database_service),
):
    """Generate a CAD/BIM export for a design."""
    design = db.get_design(request.design_id)

    analysis_data = design.get("analysis_data")
    if not analysis_data or not isinstance(analysis_data, dict):
        raise DesignNotFoundError(request.design_id)
    analysis = SketchAnalysis(**analysis_data)

    export_response = export_agent.export(analysis, request.format, request.design_id)
    return export_response


@router.get("/{export_id}", response_model=ExportResponse)
async def get_export(
    export_id: str,
    db: DatabaseService = Depends(get_database_service),
    storage: StorageService = Depends(get_storage_service),
):
    """Retrieve export metadata and presigned download URL."""
    items = _find_export_by_id(db, export_id)
    if not items:
        raise DesignNotFoundError(export_id)

    item = items[0]
    s3_key = item.get("s3_key", "")
    download_url = storage.generate_presigned_url(s3_key) if s3_key else None

    return ExportResponse(
        export_id=item["export_id"],
        design_id=item["design_id"],
        format=item.get("format", ""),
        status=item.get("status", "complete"),
        download_url=download_url,
        s3_key=s3_key,
        created_at=item.get("created_at", datetime.now(timezone.utc).isoformat()),
    )


def _find_export_by_id(db: DatabaseService, export_id: str) -> list[dict]:
    """Find export metadata by export_id using a table scan with SK filter.

    In production, a GSI on export_id would be more efficient.
    """
    try:
        response = db.table.scan(
            FilterExpression="SK = :sk",
            ExpressionAttributeValues={":sk": f"EXPORT#{export_id}"},
        )
        return response.get("Items", [])
    except Exception:
        return []
