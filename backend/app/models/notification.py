"""Notification model — persisted in-app notifications."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional, Sequence

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import NotificationType

if TYPE_CHECKING:
    from app.models.queue_entry import QueueEntry
    from app.models.user import User


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[NotificationType] = mapped_column(
        Enum(
            NotificationType,
            name="notification_type",
            native_enum=True,
            create_type=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    queue_entry_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("queue_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship()
    queue_entry: Mapped[Optional["QueueEntry"]] = relationship(
        back_populates="notifications"
    )

    @classmethod
    async def unread_count(
        cls, session: AsyncSession, user_id: int
    ) -> int:
        """Number of unread notifications for a user."""
        result = await session.execute(
            select(cls.is_read).where(
                cls.user_id == user_id, cls.is_read.is_(False)
            )
        )
        return len(result.scalars().all())

    @classmethod
    async def latest(
        cls, session: AsyncSession, user_id: int, limit: int = 20
    ) -> Sequence["Notification"]:
        """Most recent notifications for a user, newest first."""
        result = await session.execute(
            select(cls)
            .where(cls.user_id == user_id)
            .order_by(cls.created_at.desc(), cls.id.desc())
            .limit(limit)
        )
        return result.scalars().all()