from datetime import datetime
from typing import Any
from pydantic import BaseModel


class ComplianceRequest(BaseModel):
    design_id: str
    codes: list[str] = ["IBC"]


class Violation(BaseModel):
    code_category: str
    severity: str  # "critical", "high", "medium", "low"
    description: str
    location: str | None = None
    remediation: str


class ComplianceReport(BaseModel):
    report_id: str
    design_id: str
    version: int
    overall_pass: bool
    compliance_score: float
    violations: list[Violation]
    checked_codes: list[str]
    generated_at: datetime


class AccessibilityRequest(BaseModel):
    design_id: str


class AccessibilityReport(BaseModel):
    report_id: str
    design_id: str
    version: int
    ada_compliant: bool
    issues: list[dict[str, Any]]
    remediation_suggestions: list[str]
    generated_at: datetime


class EnergyRequest(BaseModel):
    design_id: str


class EnergyReport(BaseModel):
    report_id: str
    design_id: str
    version: int
    efficiency_score: float
    findings: list[dict[str, Any]]
    recommendations: list[str]
    generated_at: datetime
