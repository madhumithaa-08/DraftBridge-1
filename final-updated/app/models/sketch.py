from datetime import datetime
from typing import Any
from pydantic import BaseModel


class SketchUploadResponse(BaseModel):
    design_id: str
    sketch_id: str
    status: str  # "analyzing", "complete", "failed"
    s3_key: str
    uploaded_at: datetime


class TextBlock(BaseModel):
    text: str
    confidence: float
    bounding_box: dict[str, float]


class ArchitecturalElement(BaseModel):
    type: str  # "wall", "door", "window", "staircase", etc.
    label: str
    dimensions: dict[str, float] | None = None
    position: dict[str, float] | None = None


class Room(BaseModel):
    name: str
    area: float | None = None
    dimensions: dict[str, float] | None = None
    elements: list[ArchitecturalElement] = []


class SketchAnalysis(BaseModel):
    design_id: str
    rooms: list[Room]
    architectural_elements: list[ArchitecturalElement]
    text_annotations: list[TextBlock]
    spatial_relationships: list[dict[str, str]]
    raw_dimensions: dict[str, Any] = {}
    analyzed_at: datetime
