from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DailyQueueStatus, QueueEntryStatus


class QueueEntryCreate(BaseModel):
    service_id: int
    staff_id: int | None = Field(default=None)


class QueueEntryResponse(BaseModel):
    id: int
    daily_queue_id: int
    customer_id: int
    service_id: int
    staff_id: int | None
    token_number: int | None
    status: QueueEntryStatus
    requested_at: datetime
    accepted_at: datetime | None
    position: int | None = None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class DailyQueueResponse(BaseModel):
    id: int
    business_id: int
    queue_date: date
    status: DailyQueueStatus
    last_token: int = 0
    total_entries: int = 0
    entries: list[QueueEntryResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
