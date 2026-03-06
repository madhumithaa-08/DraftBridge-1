from datetime import datetime
from pydantic import BaseModel


class RenderRequest(BaseModel):
    design_id: str
    style: str = "photorealistic"
    materials: dict[str, str] | None = None
    lighting: str = "natural"
    resolution: str = "1024x1024"


class RenderResponse(BaseModel):
    render_id: str
    design_id: str
    image_url: str
    s3_key: str
    prompt_used: str
    created_at: datetime
