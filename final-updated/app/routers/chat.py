from fastapi import APIRouter, Depends

from app.agents.chat_agent import ChatAgent
from app.dependencies import get_chat_agent, get_database_service
from app.models.chat import ChatMessageRequest, ChatResponse, ChatHistoryResponse
from app.services.database_service import DatabaseService
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{design_id}/messages", response_model=ChatResponse)
async def send_message(
    design_id: str,
    request: ChatMessageRequest,
    chat_agent: ChatAgent = Depends(get_chat_agent),
    db: DatabaseService = Depends(get_database_service),
):
    """Send a user message and get the ChatAgent response."""
    design = db.get_design(design_id)

    analysis_data = design.get("analysis_data", {})
    descriptive_summary = ""
    if isinstance(analysis_data, dict):
        descriptive_summary = analysis_data.get("descriptive_summary", "")

    return chat_agent.send_message(design_id, request.message, descriptive_summary)


@router.get("/{design_id}/messages", response_model=ChatHistoryResponse)
async def get_messages(
    design_id: str,
    chat_agent: ChatAgent = Depends(get_chat_agent),
    db: DatabaseService = Depends(get_database_service),
):
    """Load full conversation history for a design session."""
    db.get_design(design_id)

    messages = chat_agent.get_history(design_id)
    return ChatHistoryResponse(design_id=design_id, messages=messages)
