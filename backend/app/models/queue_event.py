"""QueueEvent model — append-only audit trail of state transitions."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import QueueEntryStatus

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.queue_entry import QueueEntry
    from app.models.user import User


class QueueEvent(Base):
    __tablename__ = "queue_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    queue_entry_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("queue_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    from_status: Mapped[Optional[QueueEntryStatus]] = mapped_column(
        Enum(
            QueueEntryStatus,
            name="queue_entry_status",
            native_enum=True,
            create_type=True,
            validate_strings=True,
        ),
        nullable=True,
    )
    to_status: Mapped[QueueEntryStatus] = mapped_column(
        Enum(
            QueueEntryStatus,
            name="queue_entry_status",
            native_enum=True,
            create_type=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    actor_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        # Analytics: peak hours and daily counts by business.
        Index("ix_queue_events_business_time", "business_id", "created_at"),
    )

    queue_entry: Mapped["QueueEntry"] = relationship(back_populates="events")
    business: Mapped["Business"] = relationship()
    actor: Mapped[Optional["User"]] = relationship()