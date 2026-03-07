from datetime import datetime
from pydantic import BaseModel


class VideoRequest(BaseModel):
    design_id: str
    camera_path: str = "walkthrough"
    refined_prompt: str | None = None


class VideoResponse(BaseModel):
    video_id: str
    design_id: str
    status: str  # "processing", "complete", "failed"
    video_url: str | None = None
    s3_key: str | None = None
    invocation_arn: str | None = None
    created_at: datetime
