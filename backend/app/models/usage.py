from decimal import Decimal
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class UsageLog(Base, IDMixin, TimestampMixin):
    __tablename__ = "usage_logs"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(default=Decimal("0.0000"), nullable=False)

    user = relationship("User", back_populates="usage_logs")
