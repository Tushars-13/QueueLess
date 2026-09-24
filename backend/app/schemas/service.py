"""Service request/response schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_PRICE = Decimal("99999999.99")


def _validate_price(value: Decimal | None) -> Decimal | None:
    if value is None:
        return value
    if value < 0:
        raise ValueError("price must be zero or positive")
    if value.as_tuple().exponent < -2:
        raise ValueError("price must have at most 2 decimal places")
    return value


class ServiceCreate(BaseModel):
    """Payload for creating a service for the owner's business."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=100_000)
    price: Decimal | None = Field(default=None, ge=Decimal("0"), le=MAX_PRICE)
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)

    @field_validator("price")
    @classmethod
    def _price_scale(cls, value: Decimal | None) -> Decimal | None:
        return _validate_price(value)


class ServiceUpdate(BaseModel):
    """Partial payload for updating a service (activation excluded)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=100_000)
    price: Decimal | None = Field(default=None, ge=Decimal("0"), le=MAX_PRICE)
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)

    @field_validator("price")
    @classmethod
    def _price_scale(cls, value: Decimal | None) -> Decimal | None:
        return _validate_price(value)

    @model_validator(mode="after")
    def _reject_clearing_name(self) -> "ServiceUpdate":
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be cleared")
        return self


class ServiceActiveChange(BaseModel):
    """Activate/deactivate request body."""

    is_active: bool


class ServiceResponse(BaseModel):
    """Full service representation (owner-scoped list)."""

    id: int
    business_id: int
    name: str
    description: str | None
    price: Decimal | None
    duration_minutes: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicServiceResponse(BaseModel):
    """Service visible to customers on a public business profile.

    Only active services are ever returned, and private owner data is
    omitted (e.g. ``business_id``).
    """

    id: int
    name: str
    description: str | None
    price: Decimal | None
    duration_minutes: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)