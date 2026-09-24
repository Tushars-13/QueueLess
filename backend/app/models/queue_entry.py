"""QueueEntry model — the queue membership and lifecycle state."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import QueueEntryStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.daily_queue import DailyQueue
    from app.models.notification import Notification
    from app.models.queue_event import QueueEvent
    from app.models.service import Service
    from app.models.staff import Staff
    from app.models.user import User

# Statuses that indicate an entry is actively occupying a queue position.
ACTIVE_QUEUE_STATUSES = (
    QueueEntryStatus.REQUESTED,
    QueueEntryStatus.ACCEPTED,
    QueueEntryStatus.WAITING,
    QueueEntryStatus.CALLED,
    QueueEntryStatus.IN_SERVICE,
)


class QueueEntry(TimestampMixin, Base):
    __tablename__ = "queue_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    daily_queue_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("daily_queues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    service_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # NULL staff_id means "Any Available Staff" (general queue).
    staff_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("staff.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    status: Mapped[QueueEntryStatus] = mapped_column(
        Enum(
            QueueEntryStatus,
            name="queue_entry_status",
            native_enum=True,
            create_type=True,
            validate_strings=True,
        ),
        default=QueueEntryStatus.REQUESTED,
        server_default=text("'REQUESTED'::queue_entry_status"),
        nullable=False,
    )
    # Assigned on acceptance; NULL until then.
    token_number: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # Token must be unique within a daily queue (only for issued tokens).
        Index(
            "uq_queue_entries_token",
            "daily_queue_id",
            "token_number",
            unique=True,
            postgresql_where=text("token_number IS NOT NULL"),
        ),
        # A customer cannot be active in the same daily queue more than once.
        Index(
            "uq_queue_entries_customer_active",
            "customer_id",
            "daily_queue_id",
            unique=True,
            postgresql_where=text(
                "status IN ('REQUESTED', 'ACCEPTED', 'WAITING', "
                "'CALLED', 'IN_SERVICE')"
            ),
        ),
        # FIFO ordering + position scans.
        Index(
            "ix_queue_entries_fifo",
            "daily_queue_id",
            "staff_id",
            "status",
            "accepted_at",
            "id",
        ),
        Index(
            "ix_queue_entries_active",
            "daily_queue_id",
            "staff_id",
            postgresql_where=text(
                "status IN ('WAITING', 'CALLED', 'IN_SERVICE')"
            ),
        ),
        Index(
            "ix_queue_entries_customer_status",
            "customer_id",
            "status",
        ),
    )

    daily_queue: Mapped["DailyQueue"] = relationship(back_populates="entries")
    customer: Mapped["User"] = relationship(back_populates="queue_entries")
    service: Mapped["Service"] = relationship()
    staff: Mapped[Optional["Staff"]] = relationship(back_populates="queue_entries")
    events: Mapped[list["QueueEvent"]] = relationship(
        back_populates="queue_entry", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="queue_entry"
    )
