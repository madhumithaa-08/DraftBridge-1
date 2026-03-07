from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.agents.visualization_agent import VisualizationAgent
from app.dependencies import get_visualization_agent, get_database_service
from app.models.sketch import SketchAnalysis
from app.models.video import VideoRequest, VideoResponse
from app.services.database_service import DatabaseService
from app.utils.errors import DesignNotFoundError
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("", response_model=VideoResponse, status_code=202)
async def create_video(
    request: VideoRequest,
    viz_agent: VisualizationAgent = Depends(get_visualization_agent),
    db: DatabaseService = Depends(get_database_service),
):
    """Start walkthrough video generation for a design."""
    design = db.get_design(request.design_id)

    analysis_data = design.get("analysis_data")
    if not analysis_data or not isinstance(analysis_data, dict):
        raise DesignNotFoundError(request.design_id)
    analysis = SketchAnalysis(**analysis_data)

    # Use refined_prompt from request, or try to find the latest refined render prompt
    refined_prompt = request.refined_prompt
    if not refined_prompt:
        refined_prompt = _get_latest_refined_prompt(db, request.design_id)

    logger.info(f"Creating video for design {request.design_id}, refined_prompt={'yes' if refined_prompt else 'no'}")
    if refined_prompt:
        logger.info(f"Refined prompt preview: {refined_prompt[:150]}...")

    video_response = viz_agent.generate_video(analysis, request.design_id, refined_prompt)
    return JSONResponse(
        status_code=202,
        content=video_response.model_dump(mode="json"),
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    viz_agent: VisualizationAgent = Depends(get_visualization_agent),
    db: DatabaseService = Depends(get_database_service),
):
    """Get video status and URL. Polls Nova Reel if still processing."""
    items = _find_video_by_id(db, video_id)
    if not items:
        raise DesignNotFoundError(video_id)

    item = items[0]
    design_id = item["design_id"]
    status = item.get("status", "processing")

    if status == "processing":
        invocation_arn = item.get("invocation_arn")
        if invocation_arn:
            return viz_agent.check_video_status(invocation_arn, video_id, design_id)

    return VideoResponse(
        video_id=item["video_id"],
        design_id=design_id,
        status=status,
        video_url=item.get("video_url"),
        s3_key=item.get("s3_key"),
        invocation_arn=item.get("invocation_arn"),
        created_at=item.get("created_at", datetime.now(timezone.utc).isoformat()),
    )


def _find_video_by_id(db: DatabaseService, video_id: str) -> list[dict]:
    """Find video metadata by video_id using a table scan with filter.

    In production, a GSI on video_id would be more efficient.
    """
    try:
        response = db.table.scan(
            FilterExpression="SK = :sk",
            ExpressionAttributeValues={":sk": f"VIDEO#{video_id}"},
        )
        return response.get("Items", [])
    except Exception:
        return []


def _get_latest_refined_prompt(db: DatabaseService, design_id: str) -> str | None:
    """Find the latest refined render prompt for a design.

    Queries all RENDER# items and returns the prompt_used from the most recent
    one with style='refined', which indicates it came from chat refinement.
    """
    try:
        items = db.get_item_by_sk_prefix(design_id, "RENDER#")
        refined = [i for i in items if i.get("style") == "refined"]
        if not refined:
            return None
        latest = max(refined, key=lambda x: x.get("created_at", ""))
        return latest.get("prompt_used")
    except Exception:
        return None
