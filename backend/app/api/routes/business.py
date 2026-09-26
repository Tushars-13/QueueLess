"""Business-owner business-profile endpoints."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.exceptions import RequestValidationError
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
    BusinessListResponse,
    BusinessResponse,
    BusinessUpdate,
    PublicBusinessResponse,
)

router = APIRouter(prefix="/businesses", tags=["businesses"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

MAX_LIMIT = 100
DEFAULT_LIMIT = 20

# Half-width of the nearby-search rectangle, in degrees. Nearby search is a
# bounding box on (latitude, longitude) -- NOT a true radius/distance search --
# so results are a rectangle rather than a circle and are not distance-ranked.
# 0.1 degrees of latitude is roughly 11 km; the same value bounds longitude.
# See docs/database-design.md section 7 ("Indexes (query support)").
NEARBY_DEGREE_RADIUS = Decimal("0.1")


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


def _contains_pattern(term: str) -> str:
    """Build a case-insensitive substring LIKE pattern with wildcards escaped."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _require_coordinate_pair(
    latitude: float | None, longitude: float | None
) -> None:
    """Reject a half-specified location with the standard request-validation 422."""
    if (latitude is None) == (longitude is None):
        return
    missing = "longitude" if latitude is not None else "latitude"
    raise RequestValidationError(
        [
            {
                "type": "value_error",
                "loc": ("query", missing),
                "msg": "latitude and longitude must be provided together",
                "input": None,
            }
        ]
    )


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


@router.get(
    "",
    response_model=BusinessListResponse,
    summary="Search and discover active businesses",
)
async def list_businesses(
    db: DbSession,
    user: CurrentUser,
    q: Annotated[str | None, Query(max_length=255)] = None,
    category: Annotated[str | None, Query(max_length=100)] = None,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BusinessListResponse:
    """List active businesses for customer discovery.

    All filters are optional and combine with AND. ``q`` is a case-insensitive
    substring match on the business name, ``category`` is an exact match, and
    ``latitude``/``longitude`` (which must be supplied together) restrict
    results to a fixed bounding box -- see ``NEARBY_DEGREE_RADIUS``.
    """
    _require_coordinate_pair(latitude, longitude)

    query = select(Business).where(Business.is_active.is_(True))

    if q is not None:
        query = query.where(Business.name.ilike(_contains_pattern(q), escape="\\"))
    if category is not None:
        query = query.where(Business.category == category)

    if latitude is not None and longitude is not None:
        # NUMERIC(9,6) columns: compare against Decimal, not float.
        centre_latitude = Decimal(str(latitude))
        centre_longitude = Decimal(str(longitude))
        query = query.where(
            Business.latitude.between(
                centre_latitude - NEARBY_DEGREE_RADIUS,
                centre_latitude + NEARBY_DEGREE_RADIUS,
            ),
            Business.longitude.between(
                centre_longitude - NEARBY_DEGREE_RADIUS,
                centre_longitude + NEARBY_DEGREE_RADIUS,
            ),
        )

    result = await db.execute(
        query.order_by(Business.id).limit(limit).offset(offset)
    )
    businesses = result.scalars().all()
    return BusinessListResponse(
        items=[
            PublicBusinessResponse.model_validate(business)
            for business in businesses
        ],
        has_more=len(businesses) == limit,
    )
