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
    started_at: datetime | None = None
    completed_at: datetime | None = None
    position: int | None = None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class QueueEntryTrackingResponse(BaseModel):
    entry_id: int
    token_number: int | None
    status: QueueEntryStatus
    queue_date: date
    queue_status: DailyQueueStatus
    service_id: int
    service_name: str
    duration_minutes: int | None
    staff_id: int | None
    staff_name: str | None
    position: int | None
    customers_ahead: int | None
    estimated_wait_minutes: int | None
    recommended_arrival_at: datetime | None
    requested_at: datetime
    accepted_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None

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
