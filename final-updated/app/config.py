from pathlib import Path
from pydantic_settings import BaseSettings


def _find_env_files() -> tuple:
    """Find .env files: local first, then project root."""
    here = Path(__file__).resolve().parent.parent  # draftbridge-v2/
    candidates = [
        here / ".env",
        here.parent / ".env",
    ]
    return tuple(str(p) for p in candidates if p.exists())


class Settings(BaseSettings):
    # App
    app_name: str = "DraftBridge API"
    environment: str = "development"
    port: int = 8000
    log_level: str = "info"

    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_bucket_name: str = "draftbridge-development-assets-902605180945"
    dynamodb_table_name: str = "draftbridge-designs"

    # Bedrock Model IDs
    bedrock_text_model: str = "amazon.nova-lite-v1:0"
    bedrock_image_model: str = "amazon.nova-canvas-v1:0"
    bedrock_video_model: str = "amazon.nova-reel-v1:0"

    # Limits
    max_upload_size_mb: int = 10
    presigned_url_expiry: int = 3600

    class Config:
        env_file = _find_env_files()
        extra = "ignore"


settings = Settings()
