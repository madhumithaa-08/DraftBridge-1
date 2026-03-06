from fastapi import APIRouter, Depends

from app.dependencies import get_version_control_service
from app.models.version import (
    DesignVersion,
    VersionCompareRequest,
    VersionDiff,
    VersionHistoryResponse,
)
from app.services.version_control_service import VersionControlService

router = APIRouter(prefix="/api/versions", tags=["versions"])


@router.get("/{design_id}", response_model=VersionHistoryResponse)
def get_version_history(
    design_id: str,
    service: VersionControlService = Depends(get_version_control_service),
):
    """Return version history for a design."""
    versions = service.get_history(design_id)
    return VersionHistoryResponse(
        design_id=design_id,
        versions=versions,
        total_versions=len(versions),
    )


@router.get("/{design_id}/{version}", response_model=DesignVersion)
def get_version(
    design_id: str,
    version: int,
    service: VersionControlService = Depends(get_version_control_service),
):
    """Return a specific version of a design."""
    return service.get_version(design_id, version)


@router.post("/{design_id}/compare", response_model=VersionDiff)
def compare_versions(
    design_id: str,
    body: VersionCompareRequest,
    service: VersionControlService = Depends(get_version_control_service),
):
    """Compare two versions of a design."""
    return service.compare_versions(design_id, body.version_a, body.version_b)
