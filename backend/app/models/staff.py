"""Staff model (no accounts in MVP) and staff-services association."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    String,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.queue_entry import QueueEntry
    from app.models.service import Service


# Many-to-many: a staff member provides many services; a service has many providers.
staff_services = Table(
    "staff_services",
    Base.metadata,
    Column("staff_id", BigInteger, ForeignKey("staff.id", ondelete="CASCADE"), primary_key=True),
    Column("service_id", BigInteger, ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
)


class Staff(TimestampMixin, Base):
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    available: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("business_id", "name", name="uq_staff_business_name"),
    )

    business: Mapped["Business"] = relationship(back_populates="staff")
    services: Mapped[list["Service"]] = relationship(
        secondary=staff_services, back_populates="staff"
    )
    queue_entries: Mapped[list["QueueEntry"]] = relationship(
        back_populates="staff"
    )
