"""Tests for SketchAgent._generate_descriptive_summary — summary generation and graceful degradation."""

from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from app.agents.sketch_agent import SketchAgent
from app.services.database_service import DatabaseService
from app.services.storage_service import StorageService


@pytest.fixture
def sketch_agent_with_mocks(aws_credentials):
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
        agent = SketchAgent(bedrock, storage, db)
        yield agent, bedrock


class TestGenerateDescriptiveSummary:
    def _nova_response(self, text):
        return {"output": {"message": {"content": [{"text": text}]}}}

    def test_summary_with_rooms_and_elements(self, sketch_agent_with_mocks, sample_sketch_analysis):
        agent, bedrock = sketch_agent_with_mocks
        bedrock.invoke_model.return_value = {
            "body": MagicMock(read=lambda: __import__("json").dumps(
                self._nova_response("A spacious Living Room with a Bay Window adjacent to a Kitchen.")
            ).encode())
        }

        result = agent._generate_descriptive_summary(sample_sketch_analysis)

        assert result != ""
        assert isinstance(result, str)
        # Verify invoke_model was called
        bedrock.invoke_model.assert_called_once()

    def test_summary_returns_empty_on_bedrock_failure(self, sketch_agent_with_mocks, sample_sketch_analysis):
        agent, bedrock = sketch_agent_with_mocks
        bedrock.invoke_model.side_effect = Exception("Bedrock unavailable")

        result = agent._generate_descriptive_summary(sample_sketch_analysis)

        assert result == ""

    def test_summary_returns_empty_on_empty_response(self, sketch_agent_with_mocks, sample_sketch_analysis):
        agent, bedrock = sketch_agent_with_mocks
        bedrock.invoke_model.return_value = {
            "body": MagicMock(read=lambda: __import__("json").dumps(
                {"output": {"message": {"content": [{"text": ""}]}}}
            ).encode())
        }

        result = agent._generate_descriptive_summary(sample_sketch_analysis)

        assert result == ""

    def test_summary_prompt_includes_room_names(self, sketch_agent_with_mocks, sample_sketch_analysis):
        agent, bedrock = sketch_agent_with_mocks
        bedrock.invoke_model.return_value = {
            "body": MagicMock(read=lambda: __import__("json").dumps(
                self._nova_response("Summary text")
            ).encode())
        }

        agent._generate_descriptive_summary(sample_sketch_analysis)

        call_args = bedrock.invoke_model.call_args
        import json
        body = json.loads(call_args.kwargs.get("body", call_args[1].get("body", "{}")))
        prompt_text = body["messages"][0]["content"][0]["text"]
        assert "Living Room" in prompt_text
        assert "Kitchen" in prompt_text
