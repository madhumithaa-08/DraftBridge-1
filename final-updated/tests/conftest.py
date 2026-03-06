"""Shared test fixtures for DraftBridge test suite."""

import os

import boto3
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from moto import mock_aws

from app.models.render import RenderRequest
from app.models.sketch import (
    ArchitecturalElement,
    Room,
    SketchAnalysis,
    TextBlock,
)


# ---------------------------------------------------------------------------
# AWS credential fixture — prevents any real AWS calls
# ---------------------------------------------------------------------------

@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials via environment variables."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


# ---------------------------------------------------------------------------
# Mocked S3 fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_s3(aws_credentials):
    """Create a mocked S3 client with a test bucket."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        yield s3


# ---------------------------------------------------------------------------
# Mocked DynamoDB fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_dynamodb(aws_credentials):
    """Create a mocked DynamoDB resource with a test table (PK/SK schema)."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="test-designs",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield dynamodb


# ---------------------------------------------------------------------------
# Async test client fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_client(aws_credentials, monkeypatch):
    """Async HTTP test client wrapping the FastAPI app with mocked AWS deps."""
    # Override settings to use test bucket/table names
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-designs")

    with mock_aws():
        # Create mocked AWS resources inside the mock context
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")

        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="test-designs",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

        # Import app and override dependencies
        from app.dependencies import (
            get_bedrock_client,
            get_dynamodb_resource,
            get_s3_client,
        )
        from app.main import app

        app.dependency_overrides[get_s3_client] = lambda: s3
        app.dependency_overrides[get_dynamodb_resource] = lambda: dynamodb
        app.dependency_overrides[get_bedrock_client] = lambda: bedrock

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        # Clean up overrides
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Factory fixtures for generating test data
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_sketch_analysis():
    """Return a SketchAnalysis with sample rooms and elements."""
    from datetime import datetime, timezone

    return SketchAnalysis(
        design_id="design-001",
        rooms=[
            Room(
                name="Living Room",
                area=25.0,
                dimensions={"width": 5.0, "length": 5.0},
                elements=[
                    ArchitecturalElement(
                        type="window",
                        label="Bay Window",
                        dimensions={"width": 2.0, "height": 1.5},
                    ),
                ],
            ),
            Room(
                name="Kitchen",
                area=15.0,
                dimensions={"width": 3.0, "length": 5.0},
                elements=[
                    ArchitecturalElement(
                        type="door",
                        label="Kitchen Door",
                        dimensions={"width": 0.9, "height": 2.1},
                    ),
                ],
            ),
        ],
        architectural_elements=[
            ArchitecturalElement(type="wall", label="North Wall"),
            ArchitecturalElement(type="staircase", label="Main Staircase"),
        ],
        text_annotations=[
            TextBlock(
                text="Living Room",
                confidence=0.98,
                bounding_box={"top": 0.1, "left": 0.2, "width": 0.3, "height": 0.05},
            ),
        ],
        spatial_relationships=[
            {"from": "Living Room", "to": "Kitchen", "relation": "adjacent"},
        ],
        raw_dimensions={"total_area": 40.0},
        analyzed_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_render_request():
    """Return a RenderRequest with default options."""
    return RenderRequest(
        design_id="design-001",
        style="photorealistic",
        materials={"floor": "hardwood", "walls": "white plaster"},
        lighting="natural",
        resolution="1024x1024",
    )
