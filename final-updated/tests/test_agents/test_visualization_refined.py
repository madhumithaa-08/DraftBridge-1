"""Tests for VisualizationAgent — refined render and video generation."""

import base64
import json
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from app.agents.visualization_agent import VisualizationAgent
from app.services.database_service import DatabaseService
from app.services.storage_service import StorageService
from app.utils.errors import AWSServiceError


@pytest.fixture
def viz_agent_with_mocks(aws_credentials):
    with mock_aws():
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
        storage = StorageService(s3, "test-bucket")
        db = DatabaseService(dynamodb, "test-designs")
        bedrock = MagicMock()
        agent = VisualizationAgent(bedrock, storage, db)
        yield agent, bedrock, db, s3


def _fake_nova_canvas_response():
    """Return a fake Nova Canvas response with a base64 image."""
    fake_image = base64.b64encode(b"fake-png-bytes").decode()
    return {"images": [fake_image]}


class TestGenerateRefinedRender:
    def test_refined_render_uses_prompt_as_is(self, viz_agent_with_mocks):
        agent, bedrock, _, _ = viz_agent_with_mocks
        bedrock.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps(_fake_nova_canvas_response()).encode())
        }

        prompt = "A modern apartment with floor-to-ceiling windows and oak flooring"
        response = agent.generate_refined_render(prompt, "design-001")

        # The prompt passed to Nova Canvas should match the input
        call_args = bedrock.invoke_model.call_args
        body = json.loads(call_args.kwargs.get("body", call_args[1].get("body", "{}")))
        assert body["textToImageParams"]["text"] == prompt
        assert response.prompt_used == prompt

    def test_refined_render_stores_in_s3(self, viz_agent_with_mocks):
        agent, bedrock, _, s3 = viz_agent_with_mocks
        bedrock.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps(_fake_nova_canvas_response()).encode())
        }

        response = agent.generate_refined_render("test prompt", "design-001")

        assert response.s3_key.startswith("renders/")
        assert response.s3_key.endswith(".png")
        # Verify the file exists in S3
        obj = s3.get_object(Bucket="test-bucket", Key=response.s3_key)
        assert obj["Body"].read() == b"fake-png-bytes"

    def test_refined_render_saves_metadata_to_db(self, viz_agent_with_mocks):
        agent, bedrock, db, _ = viz_agent_with_mocks
        bedrock.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps(_fake_nova_canvas_response()).encode())
        }

        response = agent.generate_refined_render("test prompt", "design-001")

        # Check DynamoDB has the render metadata
        items = db.get_item_by_sk_prefix("design-001", "RENDER#")
        assert len(items) == 1
        assert items[0]["prompt_used"] == "test prompt"
        assert items[0]["style"] == "refined"

    def test_refined_render_raises_on_bedrock_failure(self, viz_agent_with_mocks):
        agent, bedrock, _, _ = viz_agent_with_mocks
        bedrock.invoke_model.side_effect = Exception("Nova Canvas down")

        with pytest.raises(AWSServiceError):
            agent.generate_refined_render("test prompt", "design-001")


class TestGenerateVideo:
    def test_video_params_invariant(self, viz_agent_with_mocks, sample_sketch_analysis):
        agent, bedrock, _, _ = viz_agent_with_mocks
        bedrock.start_async_invoke.return_value = {"invocationArn": "arn:aws:bedrock:us-east-1:123:async/test"}

        agent.generate_video(sample_sketch_analysis, "design-001")

        call_args = bedrock.start_async_invoke.call_args
        body = call_args.kwargs.get("modelInput", call_args[1].get("modelInput", {}))
        config = body["videoGenerationConfig"]
        assert config["durationSeconds"] == 6
        assert config["fps"] == 24
        assert config["dimension"] == "1280x720"

    def test_video_saves_processing_status(self, viz_agent_with_mocks, sample_sketch_analysis):
        agent, bedrock, db, _ = viz_agent_with_mocks
        bedrock.start_async_invoke.return_value = {"invocationArn": "arn:aws:bedrock:us-east-1:123:async/test"}

        response = agent.generate_video(sample_sketch_analysis, "design-001")

        assert response.status == "processing"
        assert response.invocation_arn == "arn:aws:bedrock:us-east-1:123:async/test"
