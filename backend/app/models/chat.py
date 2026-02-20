from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class Conversation(Base, IDMixin, TimestampMixin):
    __tablename__ = "conversations"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Chat")
    model: Mapped[str] = mapped_column(String(120), nullable=False, default="gpt-4o-mini")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="I am Nova Bot, your helpful AI assistant.")

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base, IDMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(default=0, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
