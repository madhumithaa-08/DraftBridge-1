"""Tests for DatabaseService chat message persistence."""

import boto3
import pytest
from moto import mock_aws

from app.services.database_service import DatabaseService


@pytest.fixture
def db_service(aws_credentials):
    """Create a DatabaseService with a mocked DynamoDB table."""
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
        yield DatabaseService(dynamodb, "test-designs")


class TestSaveChatMessage:
    def test_save_and_retrieve_single_message(self, db_service):
        db_service.save_chat_message("design-001", "msg-1", "user", "Add more windows")
        messages = db_service.get_chat_messages("design-001")

        assert len(messages) == 1
        assert messages[0]["message_id"] == "msg-1"
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Add more windows"
        assert messages[0]["design_id"] == "design-001"

    def test_save_multiple_messages_chronological_order(self, db_service):
        db_service.save_chat_message("design-001", "msg-1", "user", "First message")
        db_service.save_chat_message("design-001", "msg-2", "assistant", "Got it")
        db_service.save_chat_message("design-001", "msg-3", "user", "Second change")

        messages = db_service.get_chat_messages("design-001")

        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        # SK encodes timestamp, so order should be chronological
        assert messages[0]["SK"] < messages[1]["SK"] < messages[2]["SK"]

    def test_empty_history_for_new_design(self, db_service):
        messages = db_service.get_chat_messages("design-nonexistent")
        assert messages == []

    def test_messages_isolated_between_designs(self, db_service):
        db_service.save_chat_message("design-A", "msg-1", "user", "For design A")
        db_service.save_chat_message("design-B", "msg-2", "user", "For design B")

        a_messages = db_service.get_chat_messages("design-A")
        b_messages = db_service.get_chat_messages("design-B")

        assert len(a_messages) == 1
        assert len(b_messages) == 1
        assert a_messages[0]["content"] == "For design A"
        assert b_messages[0]["content"] == "For design B"

    def test_message_has_correct_pk_sk_pattern(self, db_service):
        db_service.save_chat_message("design-001", "msg-1", "user", "Hello")
        messages = db_service.get_chat_messages("design-001")

        assert messages[0]["PK"] == "DESIGN#design-001"
        assert messages[0]["SK"].startswith("CHAT#")
        assert "msg-1" in messages[0]["SK"]
