from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatMessage(BaseModel):
    message_id: str
    design_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    message: ChatMessage
    ready_to_render: bool = False
    refined_prompt: str | None = None


class ChatHistoryResponse(BaseModel):
    design_id: str
    messages: list[ChatMessage]
