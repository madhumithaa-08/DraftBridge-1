from datetime import datetime
from typing import Any
from pydantic import BaseModel


class DesignVersion(BaseModel):
    design_id: str
    version: int
    change_description: str
    analysis_snapshot: dict[str, Any] | None = None
    renders: list[str] = []
    compliance_reports: list[str] = []
    created_at: datetime


class VersionHistoryResponse(BaseModel):
    design_id: str
    versions: list[DesignVersion]
    total_versions: int


class VersionCompareRequest(BaseModel):
    version_a: int
    version_b: int


class VersionDiff(BaseModel):
    design_id: str
    version_a: int
    version_b: int
    changes: list[dict[str, Any]]
