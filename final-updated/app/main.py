from contextlib import asynccontextmanager

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import sketches, renders, videos, compliance, exports, versions, health
from app.utils.errors import DraftBridgeError
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _ensure_s3_bucket():
    """Create S3 bucket if it doesn't exist."""
    s3 = boto3.client("s3", region_name=settings.aws_region)
    try:
        s3.head_bucket(Bucket=settings.s3_bucket_name)
        logger.info(f"S3 bucket '{settings.s3_bucket_name}' exists")
    except ClientError as e:
        error_code = int(e.response["Error"]["Code"])
        if error_code == 404:
            logger.info(f"Creating S3 bucket '{settings.s3_bucket_name}'...")
            create_args = {"Bucket": settings.s3_bucket_name}
            if settings.aws_region != "us-east-1":
                create_args["CreateBucketConfiguration"] = {
                    "LocationConstraint": settings.aws_region
                }
            s3.create_bucket(**create_args)
            logger.info(f"S3 bucket '{settings.s3_bucket_name}' created")
        else:
            logger.error(f"Cannot access S3 bucket: {e}")
            raise


def _ensure_dynamodb_table():
    """Create DynamoDB table if it doesn't exist."""
    dynamodb = boto3.client("dynamodb", region_name=settings.aws_region)
    try:
        dynamodb.describe_table(TableName=settings.dynamodb_table_name)
        logger.info(f"DynamoDB table '{settings.dynamodb_table_name}' exists")
    except dynamodb.exceptions.ResourceNotFoundException:
        logger.info(f"Creating DynamoDB table '{settings.dynamodb_table_name}'...")
        dynamodb.create_table(
            TableName=settings.dynamodb_table_name,
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=settings.dynamodb_table_name)
        logger.info(f"DynamoDB table '{settings.dynamodb_table_name}' created")
    except ClientError as e:
        logger.error(f"Cannot access DynamoDB table: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} in {settings.environment} mode")
    _ensure_s3_bucket()
    _ensure_dynamodb_table()
    logger.info("AWS resources verified — ready to go")
    yield
    logger.info(f"Shutting down {settings.app_name}")


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DraftBridgeError)
async def draftbridge_error_handler(request: Request, exc: DraftBridgeError):
    logger.error(f"{exc.__class__.__name__}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.exception_handler(ClientError)
async def aws_error_handler(request: Request, exc: ClientError):
    error_code = exc.response["Error"]["Code"]
    logger.error(f"AWS ClientError: {error_code} - {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"AWS service error: {error_code}"},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Catch-all so the frontend always gets a JSON body with 'detail'."""
    logger.error(f"Unhandled exception: {exc.__class__.__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Check backend logs for details."},
    )


app.include_router(sketches.router)
app.include_router(renders.router)
app.include_router(videos.router)
app.include_router(compliance.router)
app.include_router(exports.router)
app.include_router(versions.router)
app.include_router(health.router)
