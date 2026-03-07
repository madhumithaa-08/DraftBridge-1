"""Tests for chat router — POST/GET endpoints, 404 handling, validation."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.chat import ChatMessage, ChatResponse, ChatHistoryResponse


@pytest.mark.asyncio
class TestChatRouterPost:
    async def test_send_message_returns_200(self, test_client):
        """POST /api/chat/{design_id}/messages with valid design returns 200."""
        from app.main import app
        from app.dependencies import get_chat_agent, get_database_service

        mock_db = MagicMock()
        mock_db.get_design.return_value = {
            "PK": "DESIGN#design-001", "SK": "METADATA",
            "analysis_data": {"descriptive_summary": "A modern apartment"},
        }

        mock_agent = MagicMock()
        mock_agent.send_message.return_value = ChatResponse(
            message=ChatMessage(
                message_id=str(uuid4()), design_id="design-001",
                role="assistant", content="Got it, adding windows.",
                created_at=datetime.now(timezone.utc),
            ),
            ready_to_render=False, refined_prompt=None,
        )

        app.dependency_overrides[get_database_service] = lambda: mock_db
        app.dependency_overrides[get_chat_agent] = lambda: mock_agent

        try:
            response = await test_client.post(
                "/api/chat/design-001/messages",
                json={"message": "Add more windows"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["message"]["role"] == "assistant"
            assert data["ready_to_render"] is False
        finally:
            app.dependency_overrides.pop(get_database_service, None)
            app.dependency_overrides.pop(get_chat_agent, None)

    async def test_send_message_to_nonexistent_design_returns_404(self, test_client):
        """POST /api/chat/{nonexistent}/messages returns 404."""
        response = await test_client.post(
            "/api/chat/nonexistent-design-id/messages",
            json={"message": "Hello"},
        )
        assert response.status_code == 404

    async def test_send_empty_message_returns_422(self, test_client):
        """POST with empty message body returns 422 validation error."""
        response = await test_client.post(
            "/api/chat/design-001/messages",
            json={"message": ""},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestChatRouterGet:
    async def test_get_messages_nonexistent_design_returns_404(self, test_client):
        """GET /api/chat/{nonexistent}/messages returns 404."""
        response = await test_client.get("/api/chat/nonexistent-design-id/messages")
        assert response.status_code == 404

    async def test_get_messages_returns_empty_list(self, test_client):
        """GET for design with no messages returns empty list."""
        from app.main import app
        from app.dependencies import get_chat_agent, get_database_service

        mock_db = MagicMock()
        mock_db.get_design.return_value = {"PK": "DESIGN#d1", "SK": "METADATA"}

        mock_agent = MagicMock()
        mock_agent.get_history.return_value = []

        app.dependency_overrides[get_database_service] = lambda: mock_db
        app.dependency_overrides[get_chat_agent] = lambda: mock_agent

        try:
            response = await test_client.get("/api/chat/d1/messages")
            assert response.status_code == 200
            data = response.json()
            assert data["messages"] == []
            assert data["design_id"] == "d1"
        finally:
            app.dependency_overrides.pop(get_database_service, None)
            app.dependency_overrides.pop(get_chat_agent, None)
