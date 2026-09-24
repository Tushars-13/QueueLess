"""Business, BusinessPhoto, and BusinessHour models."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.daily_queue import DailyQueue
    from app.models.service import Service
    from app.models.staff import Staff
    from app.models.user import User


class Business(TimestampMixin, Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    owner: Mapped["User"] = relationship("User", back_populates="businesses")
    photos: Mapped[list["BusinessPhoto"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    hours: Mapped[list["BusinessHour"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    services: Mapped[list["Service"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    staff: Mapped[list["Staff"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    daily_queues: Mapped[list["DailyQueue"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )


class BusinessPhoto(Base):
    __tablename__ = "business_photos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    photo_url: Mapped[str] = mapped_column(String(500), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    business: Mapped["Business"] = relationship(back_populates="photos")


class BusinessHour(Base):
    __tablename__ = "business_hours"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    open_time: Mapped[Optional[object]] = mapped_column(Time, nullable=True)
    close_time: Mapped[Optional[object]] = mapped_column(Time, nullable=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        # One hours row per weekday per business.
        UniqueConstraint("business_id", "day_of_week", name="uq_business_hours_business_day"),
        # 0 = Sunday ... 6 = Saturday.
        CheckConstraint(
            "day_of_week BETWEEN 0 AND 6", name="day_of_week_range"
        ),
    )

    business: Mapped["Business"] = relationship(back_populates="hours")
