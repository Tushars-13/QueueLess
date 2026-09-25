from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentOwner, CurrentUser
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.db.session import get_db_session
from app.models.business import Business
from app.models.daily_queue import DailyQueue
from app.models.enums import DailyQueueStatus, QueueEntryStatus, UserRole
from app.models.queue_entry import ACTIVE_QUEUE_STATUSES, QueueEntry
from app.models.queue_event import QueueEvent
from app.models.service import Service
from app.models.staff import Staff, staff_services
from app.schemas.queue import (
    DailyQueueResponse,
    QueueEntryCreate,
    QueueEntryResponse,
)

router = APIRouter(prefix="/businesses", tags=["queue"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def _owner_business(
    db: AsyncSession, owner_id: int, *, for_update: bool = False
) -> Business:
    query = select(Business).where(Business.owner_id == owner_id)
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    business = result.scalar_one_or_none()
    if business is None:
        raise NotFoundError("Business profile not found", code="business_not_found")
    return business


async def _business_for_queue(
    db: AsyncSession, business_id: int, *, for_update: bool = False
) -> Business:
    query = select(Business).where(Business.id == business_id)
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    business = result.scalar_one_or_none()
    if business is None:
        raise NotFoundError("Business not found", code="business_not_found")
    return business


def _business_local_date(business: Business) -> date:
    try:
        timezone = ZoneInfo(business.timezone)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise AppError(
            "Business timezone is invalid", code="invalid_timezone"
        ) from exc
    return datetime.now(timezone).date()


async def _today_queue_or_none(
    db: AsyncSession,
    business: Business,
    *,
    for_update: bool = False,
    queue_date: date | None = None,
) -> DailyQueue | None:
    local_date = queue_date if queue_date is not None else _business_local_date(business)
    query = select(DailyQueue).where(
        DailyQueue.business_id == business.id,
        DailyQueue.queue_date == local_date,
    )
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def _entry_positions(
    db: AsyncSession, entries: list[QueueEntry]
) -> dict[int, int]:
    if not entries:
        return {}

    queue_ids = {entry.daily_queue_id for entry in entries}
    result = await db.execute(
        select(QueueEntry)
        .where(
            QueueEntry.daily_queue_id.in_(queue_ids),
            QueueEntry.status.in_(ACTIVE_QUEUE_STATUSES),
            QueueEntry.accepted_at.is_not(None),
        )
        .order_by(QueueEntry.accepted_at, QueueEntry.id)
    )
    positions: dict[tuple[int, int | None], int] = {}
    entry_positions: dict[int, int] = {}
    for entry in result.scalars():
        queue_key = (entry.daily_queue_id, entry.staff_id)
        position = positions.get(queue_key, 0) + 1
        positions[queue_key] = position
        entry_positions[entry.id] = position
    return entry_positions


async def _entry_responses(
    db: AsyncSession, entries: list[QueueEntry]
) -> list[QueueEntryResponse]:
    positions = await _entry_positions(db, entries)
    return [
        _entry_response(entry, positions.get(entry.id))
        for entry in entries
    ]


async def _queue_with_entries(
    db: AsyncSession, queue: DailyQueue
) -> DailyQueueResponse:
    result = await db.execute(
        select(QueueEntry)
        .where(QueueEntry.daily_queue_id == queue.id)
        .order_by(QueueEntry.id)
    )
    entries = list(result.scalars())
    return DailyQueueResponse(
        id=queue.id,
        business_id=queue.business_id,
        queue_date=queue.queue_date,
        status=queue.status,
        last_token=queue.last_token,
        total_entries=len(entries),
        entries=await _entry_responses(db, entries),
    )


async def _load_queue_entry_for_update(
    db: AsyncSession, entry_id: int, business_id: int
) -> tuple[QueueEntry, DailyQueue]:
    result = await db.execute(
        select(QueueEntry, DailyQueue)
        .join(DailyQueue, QueueEntry.daily_queue_id == DailyQueue.id)
        .where(QueueEntry.id == entry_id, DailyQueue.business_id == business_id)
        .with_for_update()
    )
    row = result.one_or_none()
    if row is None:
        raise NotFoundError("Queue entry not found", code="queue_entry_not_found")
    return row


async def _ensure_open(db: AsyncSession, business: Business) -> DailyQueue:
    queue = await _today_queue_or_none(db, business, for_update=True)
    if queue is None:
        raise NotFoundError(
            "No daily queue is open for this business today",
            code="daily_queue_not_found",
        )
    if queue.status != DailyQueueStatus.OPEN:
        raise ConflictError("This queue is closed for the day", code="queue_closed")
    return queue


def _entry_response(
    entry: QueueEntry, position: int | None = None
) -> QueueEntryResponse:
    return QueueEntryResponse(
        id=entry.id,
        daily_queue_id=entry.daily_queue_id,
        customer_id=entry.customer_id,
        service_id=entry.service_id,
        staff_id=entry.staff_id,
        token_number=entry.token_number,
        status=entry.status,
        requested_at=entry.requested_at,
        accepted_at=entry.accepted_at,
        position=position,
        notes=entry.notes,
    )


def _create_event(
    db: AsyncSession,
    *,
    queue_entry: QueueEntry,
    business_id: int,
    from_status: QueueEntryStatus | None,
    to_status: QueueEntryStatus,
    actor_id: int,
) -> None:
    db.add(
        QueueEvent(
            queue_entry_id=queue_entry.id,
            business_id=business_id,
            from_status=from_status,
            to_status=to_status,
            actor_id=actor_id,
        )
    )


async def _allocate_token(db: AsyncSession, queue_id: int) -> int:
    result = await db.execute(
        update(DailyQueue)
        .where(DailyQueue.id == queue_id)
        .values(last_token=DailyQueue.last_token + 1, updated_at=func.now())
        .returning(DailyQueue.last_token)
        .execution_options(synchronize_session=False)
    )
    token = result.scalar_one_or_none()
    if token is None:
        raise NotFoundError("Daily queue not found", code="daily_queue_not_found")
    return int(token)


async def _claim_requested_entry(
    db: AsyncSession,
    entry: QueueEntry,
    target: QueueEntryStatus,
    *,
    token_number: int | None = None,
) -> bool:
    values = {"status": target, "updated_at": func.now()}
    if target == QueueEntryStatus.ACCEPTED:
        values["accepted_at"] = func.now()
        values["token_number"] = token_number

    result = await db.execute(
        update(QueueEntry)
        .where(
            QueueEntry.id == entry.id,
            QueueEntry.daily_queue_id == entry.daily_queue_id,
            QueueEntry.status == QueueEntryStatus.REQUESTED,
        )
        .values(**values)
        .returning(QueueEntry.id)
        .execution_options(synchronize_session=False)
    )
    return result.scalar_one_or_none() is not None


async def _service_for_business(
    db: AsyncSession, service_id: int, business_id: int
) -> Service:
    result = await db.execute(
        select(Service)
        .where(
            Service.id == service_id,
            Service.business_id == business_id,
            Service.is_active.is_(True),
        )
        .with_for_update()
    )
    service = result.scalar_one_or_none()
    if service is None:
        raise NotFoundError("Service not found", code="service_not_found")
    return service


async def _staff_for_business(
    db: AsyncSession, staff_id: int, business_id: int
) -> Staff:
    result = await db.execute(
        select(Staff)
        .where(
            Staff.id == staff_id,
            Staff.business_id == business_id,
            Staff.available.is_(True),
        )
        .with_for_update()
    )
    staff = result.scalar_one_or_none()
    if staff is None:
        raise NotFoundError("Staff not found", code="staff_not_found")
    return staff


async def _ensure_staff_provides(
    db: AsyncSession, staff_id: int, service_id: int
) -> None:
    result = await db.execute(
        select(staff_services.c.staff_id)
        .where(
            staff_services.c.staff_id == staff_id,
            staff_services.c.service_id == service_id,
        )
        .with_for_update()
    )
    if result.scalar_one_or_none() is None:
        raise ForbiddenError(
            "This staff member does not provide the selected service",
            code="staff_does_not_provide_service",
        )


async def _active_for_customer(
    db: AsyncSession, queue_id: int, customer_id: int
) -> QueueEntry | None:
    result = await db.execute(
        select(QueueEntry).where(
            QueueEntry.daily_queue_id == queue_id,
            QueueEntry.customer_id == customer_id,
            QueueEntry.status.in_(ACTIVE_QUEUE_STATUSES),
        )
    )
    return result.scalars().first()


@router.post(
    "/me/queue",
    response_model=DailyQueueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Open today's queue for the owner's business",
)
async def open_daily_queue(
    db: DbSession,
    owner: CurrentOwner,
) -> DailyQueueResponse:
    business = await _owner_business(db, owner.id, for_update=True)
    queue_date = _business_local_date(business)
    queue = await _today_queue_or_none(
        db, business, for_update=True, queue_date=queue_date
    )
    if queue is not None and queue.status == DailyQueueStatus.CLOSED:
        raise ConflictError("This queue is closed for the day", code="queue_closed")
    if queue is None:
        queue = DailyQueue(
            business_id=business.id,
            queue_date=queue_date,
            status=DailyQueueStatus.OPEN,
            last_token=0,
        )
        db.add(queue)

    await db.commit()
    await db.refresh(queue)
    return await _queue_with_entries(db, queue)


@router.post(
    "/me/queue/close",
    response_model=DailyQueueResponse,
    summary="Close today's queue for the owner's business",
)
async def close_daily_queue(
    db: DbSession,
    owner: CurrentOwner,
) -> DailyQueueResponse:
    business = await _owner_business(db, owner.id, for_update=True)
    queue_date = _business_local_date(business)
    queue = await _today_queue_or_none(
        db, business, for_update=True, queue_date=queue_date
    )
    if queue is None:
        raise NotFoundError(
            "No daily queue is open for this business today",
            code="daily_queue_not_found",
        )
    queue.status = DailyQueueStatus.CLOSED
    await db.commit()
    await db.refresh(queue)
    return await _queue_with_entries(db, queue)


@router.get(
    "/me/queue",
    response_model=DailyQueueResponse,
    summary="View today's queue for the owner's business",
)
async def get_my_today_queue(
    db: DbSession,
    owner: CurrentOwner,
) -> DailyQueueResponse:
    business = await _owner_business(db, owner.id)
    queue = await _today_queue_or_none(db, business)
    if queue is None:
        raise NotFoundError(
            "No daily queue is open for this business today",
            code="daily_queue_not_found",
        )
    return await _queue_with_entries(db, queue)


@router.post(
    "/me/queue/entries/{entry_id}/accept",
    response_model=QueueEntryResponse,
    summary="Accept a customer's queue request and allocate its token",
)
async def accept_entry(
    entry_id: int,
    db: DbSession,
    owner: CurrentOwner,
) -> QueueEntryResponse:
    business = await _owner_business(db, owner.id, for_update=True)
    entry, queue = await _load_queue_entry_for_update(db, entry_id, business.id)
    token = await _allocate_token(db, queue.id)
    if not await _claim_requested_entry(
        db, entry, QueueEntryStatus.ACCEPTED, token_number=token
    ):
        await db.rollback()
        raise ConflictError(
            "Queue entry is no longer awaiting acceptance",
            code="invalid_transition",
        )

    await db.refresh(entry)
    _create_event(
        db,
        queue_entry=entry,
        business_id=business.id,
        from_status=QueueEntryStatus.REQUESTED,
        to_status=QueueEntryStatus.ACCEPTED,
        actor_id=owner.id,
    )
    await db.commit()
    return (await _entry_responses(db, [entry]))[0]


@router.post(
    "/me/queue/entries/{entry_id}/reject",
    response_model=QueueEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject a customer's pending queue request",
)
async def reject_entry(
    entry_id: int,
    db: DbSession,
    owner: CurrentOwner,
) -> QueueEntryResponse:
    business = await _owner_business(db, owner.id, for_update=True)
    entry, _queue = await _load_queue_entry_for_update(db, entry_id, business.id)
    if not await _claim_requested_entry(db, entry, QueueEntryStatus.REJECTED):
        await db.rollback()
        raise ConflictError(
            "Queue entry is no longer awaiting rejection",
            code="invalid_transition",
        )

    await db.refresh(entry)
    _create_event(
        db,
        queue_entry=entry,
        business_id=business.id,
        from_status=QueueEntryStatus.REQUESTED,
        to_status=QueueEntryStatus.REJECTED,
        actor_id=owner.id,
    )
    await db.commit()
    return (await _entry_responses(db, [entry]))[0]


@router.post(
    "/{business_id}/queue",
    response_model=QueueEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request to join a business's queue",
)
async def join_queue(
    business_id: int,
    payload: QueueEntryCreate,
    db: DbSession,
    customer: CurrentUser,
) -> QueueEntryResponse:
    if customer.role != UserRole.CUSTOMER:
        raise ForbiddenError(
            "Only customers can join a queue", code="customer_required"
        )

    business = await _business_for_queue(db, business_id, for_update=True)
    queue = await _ensure_open(db, business)
    service = await _service_for_business(db, payload.service_id, business.id)

    staff_id = payload.staff_id
    if staff_id is not None:
        staff = await _staff_for_business(db, staff_id, business.id)
        await _ensure_staff_provides(db, staff.id, service.id)

    if await _active_for_customer(db, queue.id, customer.id) is not None:
        raise ConflictError(
            "You already have an active entry in this queue",
            code="already_in_queue",
        )

    entry = QueueEntry(
        daily_queue_id=queue.id,
        customer_id=customer.id,
        service_id=service.id,
        staff_id=staff_id,
        status=QueueEntryStatus.REQUESTED,
    )
    db.add(entry)
    try:
        await db.flush()
        _create_event(
            db,
            queue_entry=entry,
            business_id=business.id,
            from_status=None,
            to_status=QueueEntryStatus.REQUESTED,
            actor_id=customer.id,
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        database_error = getattr(exc.orig, "__cause__", None) or exc.orig
        if (
            getattr(database_error, "constraint_name", None)
            == "uq_queue_entries_customer_active"
        ):
            raise ConflictError(
                "You already have an active entry in this queue",
                code="already_in_queue",
            ) from exc
        raise

    await db.refresh(entry)
    return (await _entry_responses(db, [entry]))[0]
