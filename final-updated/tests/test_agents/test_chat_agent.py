"""Tests for ChatAgent — confirmation detection, system prompt, Converse API format, error handling."""

from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from app.agents.chat_agent import ChatAgent, CONFIRMATION_PHRASES
from app.services.database_service import DatabaseService
from app.services.storage_service import StorageService
from app.utils.errors import AWSServiceError


@pytest.fixture
def chat_agent_with_mocks(aws_credentials):
    """Create a ChatAgent with mocked AWS services."""
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
        agent = ChatAgent(bedrock, storage, db)
        yield agent, bedrock, db


class TestDetectConfirmation:
    """Test _detect_confirmation with various phrasings."""

    def test_ready_to_render_tag_in_assistant_text(self, chat_agent_with_mocks):
        agent, _, _ = chat_agent_with_mocks
        assert agent._detect_confirmation("Here are your changes [READY_TO_RENDER]", "generate it") is True

    def test_ready_to_render_tag_alone(self, chat_agent_with_mocks):
        agent, _, _ = chat_agent_with_mocks
        assert agent._detect_confirmation("Looks great! [READY_TO_RENDER]", "looks good") is True

    @pytest.mark.parametrize("phrase", CONFIRMATION_PHRASES)
    def test_confirmation_phrases_detected(self, chat_agent_with_mocks, phrase):
        agent, _, _ = chat_agent_with_mocks
        assert agent._detect_confirmation("Sure, I can do that.", phrase) is True

    def test_casual_feedback_not_confirmed(self, chat_agent_with_mocks):
        agent, _, _ = chat_agent_with_mocks
        assert agent._detect_confirmation("Noted, I'll adjust that.", "looks good") is False

    def test_unrelated_message_not_confirmed(self, chat_agent_with_mocks):
        agent, _, _ = chat_agent_with_mocks
        assert agent._detect_confirmation("I can help with that.", "add more windows") is False


class TestBuildSystemPrompt:
    def test_system_prompt_includes_summary(self, chat_agent_with_mocks):
        agent, _, _ = chat_agent_with_mocks
        summary = "A modern two-bedroom apartment with open kitchen"
        result = agent._build_system_prompt(summary)

        assert len(result) == 1
        assert "text" in result[0]
        assert summary in result[0]["text"]
        assert "architectural design assistant" in result[0]["text"].lower()

    def test_system_prompt_includes_ready_to_render_instructions(self, chat_agent_with_mocks):
        agent, _, _ = chat_agent_with_mocks
        result = agent._build_system_prompt("some design")
        assert "READY_TO_RENDER" in result[0]["text"]


class TestSendMessage:
    def _mock_converse_response(self, text):
        return {
            "output": {"message": {"content": [{"text": text}]}},
            "stopReason": "end_turn",
        }

    def test_send_message_calls_converse_with_full_history(self, chat_agent_with_mocks):
        agent, bedrock, db = chat_agent_with_mocks
        bedrock.converse.return_value = self._mock_converse_response("Got it, adding windows.")

        # Pre-populate one message in history
        db.save_chat_message("design-001", "old-msg", "user", "Previous message")

        response = agent.send_message("design-001", "Add more windows", "A modern apartment")

        # Verify converse was called with 2 messages (1 history + 1 new)
        call_args = bedrock.converse.call_args
        messages_sent = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert len(messages_sent) == 2
        assert messages_sent[0]["role"] == "user"
        assert messages_sent[0]["content"] == [{"text": "Previous message"}]
        assert messages_sent[1]["role"] == "user"
        assert messages_sent[1]["content"] == [{"text": "Add more windows"}]

    def test_send_message_returns_chat_response(self, chat_agent_with_mocks):
        agent, bedrock, _ = chat_agent_with_mocks
        bedrock.converse.return_value = self._mock_converse_response("Sure, noted.")

        response = agent.send_message("design-001", "Change the floor", "A modern apartment")

        assert response.message.role == "assistant"
        assert response.message.content == "Sure, noted."
        assert response.message.design_id == "design-001"
        assert response.ready_to_render is False
        assert response.refined_prompt is None

    def test_send_message_saves_both_messages_to_db(self, chat_agent_with_mocks):
        agent, bedrock, db = chat_agent_with_mocks
        bedrock.converse.return_value = self._mock_converse_response("Noted.")

        agent.send_message("design-001", "Add skylights", "A modern apartment")

        messages = db.get_chat_messages("design-001")
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Add skylights"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Noted."

    def test_send_message_on_confirmation_returns_refined_prompt(self, chat_agent_with_mocks):
        agent, bedrock, _ = chat_agent_with_mocks
        # First call: converse for the confirmation message
        bedrock.converse.side_effect = [
            self._mock_converse_response("Great! [READY_TO_RENDER] Here are your changes."),
            # Second call: converse for building the refined prompt
            self._mock_converse_response("A modern apartment with extra windows and skylights"),
        ]

        response = agent.send_message("design-001", "looks good, generate it", "A modern apartment")

        assert response.ready_to_render is True
        assert response.refined_prompt is not None
        assert len(response.refined_prompt) > 0

    def test_send_message_preserves_history_on_bedrock_failure(self, chat_agent_with_mocks):
        agent, bedrock, db = chat_agent_with_mocks
        # Pre-populate one message
        db.save_chat_message("design-001", "old-msg", "user", "Previous message")

        bedrock.converse.side_effect = Exception("Bedrock down")

        with pytest.raises(AWSServiceError):
            agent.send_message("design-001", "New message", "A modern apartment")

        # History should be unchanged — only the original message
        messages = db.get_chat_messages("design-001")
        assert len(messages) == 1
        assert messages[0]["content"] == "Previous message"
