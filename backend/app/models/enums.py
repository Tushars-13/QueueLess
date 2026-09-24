"""Domain enums shared by the ORM models.

Each enum maps to a PostgreSQL ENUM type created by the migration. Keeping a
single Python Enum per database type lets us reuse ``sqlalchemy.Enum`` with
``native_enum=True`` and ``validate_strings=True``.
"""

from enum import Enum


class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    BUSINESS_OWNER = "BUSINESS_OWNER"


class DailyQueueStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class QueueEntryStatus(str, Enum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    WAITING = "WAITING"
    CALLED = "CALLED"
    IN_SERVICE = "IN_SERVICE"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"
    NO_SHOW = "NO_SHOW"


class NotificationType(str, Enum):
    QUEUE_ACCEPTED = "QUEUE_ACCEPTED"
    REQUEST_REJECTED = "REQUEST_REJECTED"
    TURN_APPROACHING = "TURN_APPROACHING"
    TURN_REACHED = "TURN_REACHED"
    QUEUE_CLOSED = "QUEUE_CLOSED"
    GENERAL = "GENERAL"
