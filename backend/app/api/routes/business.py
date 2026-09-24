"""Business-owner business-profile endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentOwner, CurrentUser
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db_session
from app.models.business import Business, BusinessHour
from app.schemas.business import (
    BusinessCreate,
    BusinessHourResponse,
    BusinessHoursPayload,
    BusinessResponse,
    BusinessUpdate,
    PublicBusinessResponse,
)

router = APIRouter(prefix="/businesses", tags=["businesses"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def _get_owned_business(db: AsyncSession, owner_id: int) -> Business:
    """Load the business belonging to ``owner_id`` or raise 404."""
    result = await db.execute(select(Business).where(Business.owner_id == owner_id))
    business = result.scalar_one_or_none()
    if business is None:
        raise NotFoundError("Business profile not found", code="business_not_found")
    return business


async def _load_hours(db: AsyncSession, business_id: int) -> list[BusinessHour]:
    result = await db.execute(
        select(BusinessHour)
        .where(BusinessHour.business_id == business_id)
        .order_by(BusinessHour.day_of_week)
    )
    return list(result.scalars())


@router.post(
    "",
    response_model=BusinessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create the owner's business profile",
)
async def create_my_business(
    payload: BusinessCreate,
    db: DbSession,
    owner: CurrentOwner,
) -> BusinessResponse:
    """Create a business profile for the authenticated business owner."""
    existing = await db.execute(
        select(Business.id).where(Business.owner_id == owner.id)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError(
            "A business profile already exists for this owner",
            code="business_already_exists",
        )

    business = Business(owner_id=owner.id, **payload.model_dump())
    db.add(business)
    await db.commit()
    await db.refresh(business)
    return BusinessResponse.model_validate(business)


@router.get(
    "/me",
    response_model=BusinessResponse,
    summary="Get the owner's business profile",
)
async def get_my_business(
    db: DbSession,
    owner: CurrentOwner,
) -> BusinessResponse:
    business = await _get_owned_business(db, owner.id)
    return BusinessResponse.model_validate(business)


@router.patch(
    "/me",
    response_model=BusinessResponse,
    summary="Update the owner's business profile",
)
async def update_my_business(
    payload: BusinessUpdate,
    db: DbSession,
    owner: CurrentOwner,
) -> BusinessResponse:
    business = await _get_owned_business(db, owner.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(business, field, value)
    await db.commit()
    await db.refresh(business)
    return BusinessResponse.model_validate(business)


@router.get(
    "/me/hours",
    response_model=list[BusinessHourResponse],
    summary="Get the owner's weekly opening hours",
)
async def get_my_hours(
    db: DbSession,
    owner: CurrentOwner,
) -> list[BusinessHourResponse]:
    business = await _get_owned_business(db, owner.id)
    rows = await _load_hours(db, business.id)
    return [BusinessHourResponse.model_validate(row) for row in rows]


@router.put(
    "/me/hours",
    response_model=list[BusinessHourResponse],
    summary="Replace the owner's weekly opening hours",
)
async def replace_my_hours(
    payload: BusinessHoursPayload,
    db: DbSession,
    owner: CurrentOwner,
) -> list[BusinessHourResponse]:
    """Replace the full weekly schedule for the owner's business."""
    business = await _get_owned_business(db, owner.id)

    await db.execute(
        delete(BusinessHour).where(BusinessHour.business_id == business.id)
    )
    db.add_all(
        BusinessHour(business_id=business.id, **hour.model_dump())
        for hour in payload.hours
    )
    await db.commit()

    rows = await _load_hours(db, business.id)
    return [BusinessHourResponse.model_validate(row) for row in rows]


@router.get(
    "/{business_id}",
    response_model=PublicBusinessResponse,
    summary="View a business profile by id (authenticated user)",
)
async def get_business_by_id(
    business_id: int,
    db: DbSession,
    user: CurrentUser,
) -> PublicBusinessResponse:
    """Return a business profile to any authenticated user; 404 if missing."""
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    if business is None:
        raise NotFoundError("Business not found", code="business_not_found")
    return PublicBusinessResponse.model_validate(business)