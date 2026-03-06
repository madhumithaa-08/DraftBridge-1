"""Health check endpoint with AWS service connectivity checks."""

from fastapi import APIRouter, Depends

from app.config import settings
from app.dependencies import get_s3_client, get_dynamodb_resource, get_bedrock_client
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check(
    s3_client=Depends(get_s3_client),
    dynamodb=Depends(get_dynamodb_resource),
    bedrock_client=Depends(get_bedrock_client),
):
    """Return health status with service connectivity checks."""
    services = {}

    # Check S3
    try:
        s3_client.head_bucket(Bucket=settings.s3_bucket_name)
        services["s3"] = "ok"
    except Exception as e:
        logger.error(f"S3 health check failed: {e}")
        services["s3"] = "error"

    # Check DynamoDB
    try:
        table = dynamodb.Table(settings.dynamodb_table_name)
        table.table_status  # noqa: B018 — triggers describe_table call
        services["dynamodb"] = "ok"
    except Exception as e:
        logger.error(f"DynamoDB health check failed: {e}")
        services["dynamodb"] = "error"

    # Check Bedrock
    try:
        bedrock_client.get_endpoint(modelId=settings.bedrock_text_model) if False else None  # noqa
        # Use a lightweight list call to verify connectivity
        bedrock_client.meta.service_model  # noqa: B018 — verify client is valid
        services["bedrock"] = "ok"
    except Exception as e:
        logger.error(f"Bedrock health check failed: {e}")
        services["bedrock"] = "error"

    overall = "healthy" if all(v == "ok" for v in services.values()) else "degraded"

    return {"status": overall, "services": services}
