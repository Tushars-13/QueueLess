"""DailyQueue model — one queue per business per operating day."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, Enum, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DailyQueueStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.queue_entry import QueueEntry


class DailyQueue(TimestampMixin, Base):
    __tablename__ = "daily_queues"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    queue_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[DailyQueueStatus] = mapped_column(
        Enum(
            DailyQueueStatus,
            name="daily_queue_status",
            native_enum=True,
            create_type=True,
            validate_strings=True,
        ),
        default=DailyQueueStatus.CLOSED,
        server_default=text("'CLOSED'::daily_queue_status"),
        nullable=False,
    )
    # Token counter used for concurrency-safe daily token allocation.
    last_token: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default=text("0"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "business_id", "queue_date", name="uq_daily_queues_business_date"
        ),
    )

    business: Mapped["Business"] = relationship(back_populates="daily_queues")
    entries: Mapped[list["QueueEntry"]] = relationship(back_populates="daily_queue")
