"""Staff management (owner) and public staff availability endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentOwner, CurrentUser
from app.api.routes.business import _get_owned_business
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.db.session import get_db_session
from app.models.business import Business
from app.models.service import Service
from app.models.staff import Staff, staff_services
from app.schemas.service import (
    PublicServiceResponse,
    ServiceResponse,
)
from app.schemas.staff import (
    PublicStaffResponse,
    StaffAvailableChange,
    StaffCreate,
    StaffResponse,
    StaffUpdate,
)

router = APIRouter(prefix="/businesses", tags=["staff"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def _owner_business_id(db: AsyncSession, owner_id: int) -> int:
    """Return the id of the owner's business profile (404 if none exists)."""
    return (await _get_owned_business(db, owner_id)).id


async def _staff_for_owner(
    db: AsyncSession, staff_id: int, business_id: int
) -> Staff:
    """Load a staff row owned by ``business_id`` (404 missing, 403 foreign)."""
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if staff is None:
        raise NotFoundError("Staff not found", code="staff_not_found")
    if staff.business_id != business_id:
        raise ForbiddenError("You do not own this staff member", code="not_owner")
    return staff


async def _staff_name_taken(
    db: AsyncSession,
    business_id: int,
    name: str,
    *,
    exclude_id: int | None = None,
) -> bool:
    query = select(Staff.id).where(
        Staff.business_id == business_id, Staff.name == name
    )
    if exclude_id is not None:
        query = query.where(Staff.id != exclude_id)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def _service_for_business(
    db: AsyncSession, service_id: int, business_id: int
) -> Service:
    """Load a service owned by ``business_id`` (404 missing, 403 foreign)."""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if service is None:
        raise NotFoundError("Service not found", code="service_not_found")
    if service.business_id != business_id:
        raise ForbiddenError("You do not own this service", code="not_owner")
    return service


@router.post(
    "/me/staff",
    response_model=StaffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a staff member for the owner's business",
)
async def create_my_staff(
    payload: StaffCreate,
    db: DbSession,
    owner: CurrentOwner,
) -> StaffResponse:
    business_id = await _owner_business_id(db, owner.id)

    if await _staff_name_taken(db, business_id, payload.name):
        raise ConflictError(
            "A staff member with this name already exists",
            code="staff_already_exists",
        )

    staff = Staff(business_id=business_id, **payload.model_dump(exclude_unset=True))
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    return StaffResponse.model_validate(staff)


@router.get(
    "/me/staff",
    response_model=list[StaffResponse],
    summary="List the owner's staff members",
)
async def list_my_staff(
    db: DbSession,
    owner: CurrentOwner,
) -> list[StaffResponse]:
    business_id = await _owner_business_id(db, owner.id)
    result = await db.execute(
        select(Staff).where(Staff.business_id == business_id).order_by(Staff.id)
    )
    return [StaffResponse.model_validate(row) for row in result.scalars()]


@router.patch(
    "/me/staff/{staff_id}",
    response_model=StaffResponse,
    summary="Update a staff member (name/title only)",
)
async def update_my_staff(
    staff_id: int,
    payload: StaffUpdate,
    db: DbSession,
    owner: CurrentOwner,
) -> StaffResponse:
    business_id = await _owner_business_id(db, owner.id)
    staff = await _staff_for_owner(db, staff_id, business_id)

    changes = payload.model_dump(exclude_unset=True)
    new_name = changes.get("name")
    if new_name is not None and await _staff_name_taken(
        db, business_id, new_name, exclude_id=staff.id
    ):
        raise ConflictError(
            "A staff member with this name already exists",
            code="staff_already_exists",
        )

    for field, value in changes.items():
        setattr(staff, field, value)
    await db.commit()
    await db.refresh(staff)
    return StaffResponse.model_validate(staff)


@router.patch(
    "/me/staff/{staff_id}/available",
    response_model=StaffResponse,
    summary="Activate or deactivate a staff member's availability",
)
async def set_my_staff_available(
    staff_id: int,
    payload: StaffAvailableChange,
    db: DbSession,
    owner: CurrentOwner,
) -> StaffResponse:
    business_id = await _owner_business_id(db, owner.id)
    staff = await _staff_for_owner(db, staff_id, business_id)

    staff.available = payload.available
    await db.commit()
    await db.refresh(staff)
    return StaffResponse.model_validate(staff)


@router.get(
    "/me/staff/{staff_id}/services",
    response_model=list[ServiceResponse],
    summary="List the services provided by one of the owner's staff members",
)
async def list_my_staff_services(
    staff_id: int,
    db: DbSession,
    owner: CurrentOwner,
) -> list[ServiceResponse]:
    business_id = await _owner_business_id(db, owner.id)
    staff = await _staff_for_owner(db, staff_id, business_id)

    result = await db.execute(
        select(Service)
        .join(staff_services, staff_services.c.service_id == Service.id)
        .where(staff_services.c.staff_id == staff.id)
        .order_by(Service.id)
    )
    return [ServiceResponse.model_validate(row) for row in result.scalars()]


@router.post(
    "/me/staff/{staff_id}/services/{service_id}",
    response_model=ServiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign a service to one of the owner's staff members",
)
async def assign_my_staff_service(
    staff_id: int,
    service_id: int,
    db: DbSession,
    owner: CurrentOwner,
) -> ServiceResponse:
    business_id = await _owner_business_id(db, owner.id)
    staff = await _staff_for_owner(db, staff_id, business_id)
    service = await _service_for_business(db, service_id, business_id)

    existing = await db.execute(
        select(staff_services.c.service_id).where(
            staff_services.c.staff_id == staff.id,
            staff_services.c.service_id == service.id,
        )
    )
    if existing.scalar_one_or_none() is None:
        await db.execute(
            staff_services.insert().values(
                staff_id=staff.id, service_id=service.id
            )
        )
        await db.commit()

    return ServiceResponse.model_validate(service)


@router.delete(
    "/me/staff/{staff_id}/services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a service from one of the owner's staff members",
)
async def remove_my_staff_service(
    staff_id: int,
    service_id: int,
    db: DbSession,
    owner: CurrentOwner,
) -> None:
    business_id = await _owner_business_id(db, owner.id)
    staff = await _staff_for_owner(db, staff_id, business_id)
    service = await _service_for_business(db, service_id, business_id)

    await db.execute(
        staff_services.delete().where(
            staff_services.c.staff_id == staff.id,
            staff_services.c.service_id == service.id,
        )
    )
    await db.commit()
    return None


@router.get(
    "/{business_id}/staff",
    response_model=list[PublicStaffResponse],
    summary="View staff and their availability for a business (authenticated user)",
)
async def list_public_staff(
    business_id: int,
    db: DbSession,
    user: CurrentUser,
) -> list[PublicStaffResponse]:
    business_result = await db.execute(
        select(Business.id).where(Business.id == business_id)
    )
    if business_result.scalar_one_or_none() is None:
        raise NotFoundError("Business not found", code="business_not_found")

    result = await db.execute(
        select(Staff).where(Staff.business_id == business_id).order_by(Staff.id)
    )
    return [PublicStaffResponse.model_validate(row) for row in result.scalars()]
