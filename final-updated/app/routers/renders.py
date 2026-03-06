from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.agents.visualization_agent import VisualizationAgent
from app.dependencies import get_visualization_agent, get_storage_service, get_database_service
from app.models.render import RenderRequest, RenderResponse
from app.models.sketch import SketchAnalysis
from app.services.database_service import DatabaseService
from app.services.storage_service import StorageService
from app.utils.errors import DesignNotFoundError
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/renders", tags=["renders"])


@router.post("", response_model=RenderResponse)
async def create_render(
    request: RenderRequest,
    viz_agent: VisualizationAgent = Depends(get_visualization_agent),
    db: DatabaseService = Depends(get_database_service),
):
    """Generate a photorealistic render for a design."""
    design = db.get_design(request.design_id)

    analysis_data = design.get("analysis_data")
    if not analysis_data or not isinstance(analysis_data, dict):
        raise DesignNotFoundError(request.design_id)
    analysis = SketchAnalysis(**analysis_data)

    render_response = viz_agent.generate_render(analysis, request)
    return render_response


@router.get("/{render_id}", response_model=RenderResponse)
async def get_render(
    render_id: str,
    db: DatabaseService = Depends(get_database_service),
    storage: StorageService = Depends(get_storage_service),
):
    """Retrieve render metadata and presigned URL."""
    # Query for render metadata across all designs
    # render_id is unique, but we need the design_id to look it up
    # The render metadata is stored with SK=RENDER#{render_id}
    # We need to scan or use a known design_id; for now, we extract from the item
    # A practical approach: the client should know the design_id, but for a GET by render_id
    # we'll search using the render_id in the SK
    items = _find_render_by_id(db, render_id)
    if not items:
        raise DesignNotFoundError(render_id)

    item = items[0]
    s3_key = item.get("s3_key", "")
    image_url = storage.generate_presigned_url(s3_key) if s3_key else ""

    return RenderResponse(
        render_id=item["render_id"],
        design_id=item["design_id"],
        image_url=image_url,
        s3_key=s3_key,
        prompt_used=item.get("prompt_used", ""),
        created_at=item.get("created_at", datetime.now(timezone.utc).isoformat()),
    )


def _find_render_by_id(db: DatabaseService, render_id: str) -> list[dict]:
    """Find render metadata by render_id using a table scan with filter.

    In production, a GSI on render_id would be more efficient.
    For now, we use the SK pattern to query if design_id is embedded,
    or fall back to scanning.
    """
    try:
        response = db.table.scan(
            FilterExpression="SK = :sk",
            ExpressionAttributeValues={":sk": f"RENDER#{render_id}"},
        )
        return response.get("Items", [])
    except Exception:
        return []
