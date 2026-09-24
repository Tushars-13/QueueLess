"""Service management (owner) and public service listing endpoints."""

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
from app.schemas.service import (
    PublicServiceResponse,
    ServiceActiveChange,
    ServiceCreate,
    ServiceResponse,
    ServiceUpdate,
)

router = APIRouter(prefix="/businesses", tags=["services"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def _owner_business_id(db: AsyncSession, owner_id: int) -> int:
    """Return the id of the owner's business (404 if none exists)."""
    return (await _get_owned_business(db, owner_id)).id


async def _service_for_owner(
    db: AsyncSession, service_id: int, business_id: int
) -> Service:
    """Load a service owned by ``business_id``; 403 for foreign, 404 if missing."""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if service is None:
        raise NotFoundError("Service not found", code="service_not_found")
    if service.business_id != business_id:
        raise ForbiddenError("You do not own this service", code="not_owner")
    return service


async def _service_name_taken(
    db: AsyncSession,
    business_id: int,
    name: str,
    *,
    exclude_id: int | None = None,
) -> bool:
    query = select(Service.id).where(
        Service.business_id == business_id, Service.name == name
    )
    if exclude_id is not None:
        query = query.where(Service.id != exclude_id)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


@router.post(
    "/me/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a service for the owner's business",
)
async def create_my_service(
    payload: ServiceCreate,
    db: DbSession,
    owner: CurrentOwner,
) -> ServiceResponse:
    business_id = await _owner_business_id(db, owner.id)

    if await _service_name_taken(db, business_id, payload.name):
        raise ConflictError(
            "A service with this name already exists",
            code="service_already_exists",
        )

    service = Service(business_id=business_id, **payload.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return ServiceResponse.model_validate(service)


@router.get(
    "/me/services",
    response_model=list[ServiceResponse],
    summary="List the owner's services",
)
async def list_my_services(
    db: DbSession,
    owner: CurrentOwner,
) -> list[ServiceResponse]:
    business_id = await _owner_business_id(db, owner.id)
    result = await db.execute(
        select(Service)
        .where(Service.business_id == business_id)
        .order_by(Service.id)
    )
    return [ServiceResponse.model_validate(row) for row in result.scalars()]


@router.patch(
    "/me/services/{service_id}",
    response_model=ServiceResponse,
    summary="Update one of the owner's services",
)
async def update_my_service(
    service_id: int,
    payload: ServiceUpdate,
    db: DbSession,
    owner: CurrentOwner,
) -> ServiceResponse:
    business_id = await _owner_business_id(db, owner.id)
    service = await _service_for_owner(db, service_id, business_id)

    changes = payload.model_dump(exclude_unset=True)
    new_name = changes.get("name")
    if new_name is not None and await _service_name_taken(
        db, business_id, new_name, exclude_id=service.id
    ):
        raise ConflictError(
            "A service with this name already exists",
            code="service_already_exists",
        )

    for field, value in changes.items():
        setattr(service, field, value)
    await db.commit()
    await db.refresh(service)
    return ServiceResponse.model_validate(service)


@router.patch(
    "/me/services/{service_id}/active",
    response_model=ServiceResponse,
    summary="Activate or deactivate one of the owner's services",
)
async def set_my_service_active(
    service_id: int,
    payload: ServiceActiveChange,
    db: DbSession,
    owner: CurrentOwner,
) -> ServiceResponse:
    business_id = await _owner_business_id(db, owner.id)
    service = await _service_for_owner(db, service_id, business_id)

    service.is_active = payload.is_active
    await db.commit()
    await db.refresh(service)
    return ServiceResponse.model_validate(service)


@router.get(
    "/{business_id}/services",
    response_model=list[PublicServiceResponse],
    summary="View active services for a business (authenticated user)",
)
async def list_public_services(
    business_id: int,
    db: DbSession,
    user: CurrentUser,
) -> list[PublicServiceResponse]:
    """Return only active services for a business; 404 if the business is missing."""
    business_result = await db.execute(
        select(Business.id).where(Business.id == business_id)
    )
    if business_result.scalar_one_or_none() is None:
        raise NotFoundError("Business not found", code="business_not_found")

    result = await db.execute(
        select(Service)
        .where(Service.business_id == business_id, Service.is_active.is_(True))
        .order_by(Service.id)
    )
    return [PublicServiceResponse.model_validate(row) for row in result.scalars()]