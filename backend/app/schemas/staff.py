"""Staff request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StaffCreate(BaseModel):
    """Payload for creating a staff member for the owner's business."""

    name: str = Field(min_length=1, max_length=255)
    title: str | None = Field(default=None, max_length=255)


class StaffUpdate(BaseModel):
    """Partial payload for updating a staff member (availability excluded)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    title: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _reject_clearing_name(self) -> "StaffUpdate":
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be cleared")
        return self


class StaffAvailableChange(BaseModel):
    """Toggle a staff member's availability."""

    available: bool


class StaffResponse(BaseModel):
    """Full staff representation (owner-scoped)."""

    id: int
    business_id: int
    name: str
    title: str | None
    available: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicStaffResponse(BaseModel):
    """Staff visible to customers on a public business profile.

    Availability is shown so customers can see who is on duty; private
    owner data (e.g. ``business_id``) is omitted.
    """

    id: int
    name: str
    title: str | None
    available: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
