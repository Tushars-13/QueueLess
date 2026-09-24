"""User model (Customer and Business Owner)."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin

# ANSI email length limit is a common safe maximum.
EMAIL_MAX_LEN = 254


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(
        String(EMAIL_MAX_LEN), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=True,
            create_type=True,
            validate_strings=True,
        ),
        nullable=False,
    )

    # Relationships (typed when TYPE_CHECKING to avoid circular imports).
    if TYPE_CHECKING:
        from app.models.business import Business

        businesses: Mapped[list["Business"]]
        queue_entries: Mapped[list]  # QueueEntry

    businesses = relationship("Business", back_populates="owner")
    queue_entries = relationship("QueueEntry", back_populates="customer")
