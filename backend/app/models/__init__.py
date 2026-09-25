"""ORM model registry.

Importing this module registers every model on ``Base.metadata`` so Alembic
automation picks up the full schema.
"""

from app.db.base import Base
from app.models.business import Business, BusinessHour, BusinessPhoto
from app.models.daily_queue import DailyQueue
from app.models.enums import (
    DailyQueueStatus,
    NotificationType,
    QueueEntryStatus,
    UserRole,
)
from app.models.mixins import TimestampMixin
from app.models.notification import Notification
from app.models.queue_entry import (
    ACTIVE_QUEUE_STATUSES,
    QUEUE_POSITION_STATUSES,
    QueueEntry,
)
from app.models.queue_event import QueueEvent
from app.models.service import Service
from app.models.staff import Staff, staff_services
from app.models.user import User

__all__ = [
    "ACTIVE_QUEUE_STATUSES",
    "QUEUE_POSITION_STATUSES",
    "Base",
    "Business",
    "BusinessHour",
    "BusinessPhoto",
    "DailyQueue",
    "DailyQueueStatus",
    "Notification",
    "NotificationType",
    "QueueEntry",
    "QueueEntryStatus",
    "QueueEvent",
    "Service",
    "Staff",
    "TimestampMixin",
    "User",
    "UserRole",
    "staff_services",
]