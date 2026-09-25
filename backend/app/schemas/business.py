"""Business profile and opening-hours request/response schemas."""

from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError("timezone must be a valid IANA timezone") from exc
    return value


class BusinessCreate(BaseModel):
    """Payload for creating the logged-in owner's business profile."""

    name: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=100_000)
    address: str | None = Field(default=None, max_length=255)
    latitude: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal | None = Field(
        default=None, ge=Decimal("-180"), le=Decimal("180")
    )
    timezone: str = Field(default="UTC", min_length=1, max_length=64)

    @field_validator("timezone")
    @classmethod
    def _timezone_must_be_valid(cls, value: str) -> str:
        return _validate_timezone(value)

    @model_validator(mode="after")
    def _coordinates_together(self) -> "BusinessCreate":
        has_latitude = self.latitude is not None
        has_longitude = self.longitude is not None
        if has_latitude != has_longitude:
            raise ValueError("latitude and longitude must be provided together")
        return self


class BusinessUpdate(BaseModel):
    """Partial payload for updating the owner's business profile."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=100_000)
    address: str | None = Field(default=None, max_length=255)
    latitude: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal | None = Field(
        default=None, ge=Decimal("-180"), le=Decimal("180")
    )
    timezone: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("timezone")
    @classmethod
    def _timezone_must_be_valid(cls, value: str | None) -> str | None:
        return _validate_timezone(value) if value is not None else None

    @model_validator(mode="after")
    def _coordinates_together(self) -> "BusinessUpdate":
        has_latitude = self.latitude is not None
        has_longitude = self.longitude is not None
        if has_latitude != has_longitude:
            raise ValueError("latitude and longitude must be provided together")
        return self

    @model_validator(mode="after")
    def _reject_clearing_required_fields(self) -> "BusinessUpdate":
        provided = self.model_fields_set
        for field in ("name", "category", "timezone"):
            if field in provided and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be cleared")
        return self


class BusinessResponse(BaseModel):
    """Public business profile representation (owner-scoped)."""

    id: int
    owner_id: int
    name: str
    category: str
    description: str | None
    address: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicBusinessResponse(BaseModel):
    """Public business profile visible to any authenticated user.

    Deliberately omits owner data (e.g. ``owner_id``).
    """

    id: int
    name: str
    category: str
    description: str | None
    address: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BusinessHourInput(BaseModel):
    """A single weekday's opening hours.

    ``day_of_week`` follows the database convention: 0 = Sunday ... 6 = Saturday.
    """

    day_of_week: int = Field(ge=0, le=6)
    open_time: time | None = None
    close_time: time | None = None
    is_closed: bool = False

    @model_validator(mode="after")
    def _validate_times(self) -> "BusinessHourInput":
        if self.is_closed:
            if self.open_time is not None or self.close_time is not None:
                raise ValueError("closed days must not have open or close times")
            return self
        if self.open_time is None or self.close_time is None:
            raise ValueError("open days require both open_time and close_time")
        if self.close_time <= self.open_time:
            raise ValueError("close_time must be after open_time")
        return self


class BusinessHoursPayload(BaseModel):
    """Full weekly schedule (one entry per configured weekday)."""

    hours: list[BusinessHourInput] = Field(min_length=1, max_length=7)

    @model_validator(mode="after")
    def _unique_days(self) -> "BusinessHoursPayload":
        days = [hour.day_of_week for hour in self.hours]
        if len(days) != len(set(days)):
            raise ValueError("each weekday may be configured at most once")
        return self


class BusinessHourResponse(BaseModel):
    """A persisted opening-hours row."""

    id: int
    business_id: int
    day_of_week: int
    open_time: time | None
    close_time: time | None
    is_closed: bool

    model_config = ConfigDict(from_attributes=True)