from fastapi import APIRouter, Depends

from app.agents.compliance_agent import ComplianceAgent
from app.dependencies import get_compliance_agent, get_database_service
from app.models.compliance import (
    AccessibilityReport,
    AccessibilityRequest,
    ComplianceReport,
    ComplianceRequest,
    EnergyReport,
    EnergyRequest,
)
from app.models.sketch import SketchAnalysis
from app.services.database_service import DatabaseService
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.post("/building-code", response_model=ComplianceReport)
async def check_building_code(
    request: ComplianceRequest,
    agent: ComplianceAgent = Depends(get_compliance_agent),
    db: DatabaseService = Depends(get_database_service),
):
    """Run building code compliance check against a design."""
    design = db.get_design(request.design_id)
    analysis_data = design.get("analysis_data")
    if not analysis_data or not isinstance(analysis_data, dict):
        from app.utils.errors import DesignNotFoundError
        raise DesignNotFoundError(request.design_id)
    analysis = SketchAnalysis(**analysis_data)
    return agent.check_compliance(analysis, request.codes)


@router.post("/accessibility", response_model=AccessibilityReport)
async def check_accessibility(
    request: AccessibilityRequest,
    agent: ComplianceAgent = Depends(get_compliance_agent),
    db: DatabaseService = Depends(get_database_service),
):
    """Run ADA accessibility validation against a design."""
    design = db.get_design(request.design_id)
    analysis_data = design.get("analysis_data")
    if not analysis_data or not isinstance(analysis_data, dict):
        from app.utils.errors import DesignNotFoundError
        raise DesignNotFoundError(request.design_id)
    analysis = SketchAnalysis(**analysis_data)
    return agent.validate_accessibility(analysis)


@router.post("/energy", response_model=EnergyReport)
async def check_energy(
    request: EnergyRequest,
    agent: ComplianceAgent = Depends(get_compliance_agent),
    db: DatabaseService = Depends(get_database_service),
):
    """Run energy efficiency analysis against a design."""
    design = db.get_design(request.design_id)
    analysis_data = design.get("analysis_data")
    if not analysis_data or not isinstance(analysis_data, dict):
        from app.utils.errors import DesignNotFoundError
        raise DesignNotFoundError(request.design_id)
    analysis = SketchAnalysis(**analysis_data)
    return agent.analyze_energy(analysis)
