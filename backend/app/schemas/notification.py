from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import NotificationType


class NotificationResponse(BaseModel):
    id: int
    type: NotificationType
    title: str
    body: str
    queue_entry_id: int | None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
    has_more: bool
