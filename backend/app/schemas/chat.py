from datetime import datetime
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=255)
    model: str = Field(default="gpt-4o-mini", max_length=120)
    system_prompt: str = Field(default="I am Nova Bot, your helpful AI assistant.", max_length=8000)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ConversationOut(BaseModel):
    id: int
    title: str
    model: str
    system_prompt: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSendRequest(BaseModel):
    conversation_id: int
    message: str = Field(min_length=1, max_length=12000)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=4000)
    model: str | None = Field(default=None, max_length=120)
    system_prompt: str | None = Field(default=None, max_length=8000)


class ChatSendResponse(BaseModel):
    assistant_message: MessageOut
    user_message: MessageOut


class ChatHistoryResponse(BaseModel):
    conversation: ConversationOut
    messages: list[MessageOut]
