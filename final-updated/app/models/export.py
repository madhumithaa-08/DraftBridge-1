from datetime import datetime
from pydantic import BaseModel, field_validator


class ExportRequest(BaseModel):
    design_id: str
    format: str

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        allowed = {"DWG", "DXF", "RVT", "IFC"}
        if v.upper() not in allowed:
            raise ValueError(f"Unsupported format: {v}. Supported: {allowed}")
        return v.upper()


class ExportResponse(BaseModel):
    export_id: str
    design_id: str
    format: str
    status: str  # "generating", "complete", "failed"
    download_url: str | None = None
    s3_key: str | None = None
    created_at: datetime
