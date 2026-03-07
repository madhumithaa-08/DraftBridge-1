from datetime import datetime, timezone

from fastapi import APIRouter, Depends, UploadFile, File

from app.agents.sketch_agent import SketchAgent
from app.dependencies import get_sketch_agent, get_storage_service, get_database_service
from app.models.sketch import SketchUploadResponse
from app.services.database_service import DatabaseService
from app.services.storage_service import StorageService
from app.utils.errors import UnsupportedFormatError
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/sketches", tags=["sketches"])

SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("", response_model=SketchUploadResponse)
async def upload_sketch(
    file: UploadFile = File(...),
    sketch_agent: SketchAgent = Depends(get_sketch_agent),
    storage: StorageService = Depends(get_storage_service),
    db: DatabaseService = Depends(get_database_service),
):
    """Upload and analyze a sketch image."""
    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise UnsupportedFormatError(file.content_type, {"JPEG", "PNG", "WEBP"})

    image_bytes = await file.read()

    s3_key = storage.store_file(image_bytes, "sketches/", file.filename or "sketch.png", file.content_type)

    design_id = db.create_design(sketch_s3_key=s3_key)

    analysis = sketch_agent.analyze(image_bytes, design_id, file.content_type or "image/png")

    db.update_design(design_id, {
        "status": "complete",
        "analysis_data": analysis.model_dump(mode="json"),
    })

    return SketchUploadResponse(
        design_id=design_id,
        sketch_id=design_id,
        status="complete",
        s3_key=s3_key,
        uploaded_at=datetime.now(timezone.utc),
        descriptive_summary=analysis.descriptive_summary,
        rooms=analysis.rooms,
        architectural_elements=analysis.architectural_elements,
    )


@router.get("/{sketch_id}")
async def get_sketch(
    sketch_id: str,
    db: DatabaseService = Depends(get_database_service),
):
    """Retrieve sketch analysis results."""
    design = db.get_design(sketch_id)
    return design
