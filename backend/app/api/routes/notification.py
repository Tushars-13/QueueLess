from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db_session
from app.models.notification import Notification
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

MAX_LIMIT = 100
DEFAULT_LIMIT = 20


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List the authenticated user's notifications, newest first",
)
async def list_notifications(
    db: DbSession,
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NotificationListResponse:
    notifications = await Notification.latest(
        db, current_user.id, limit=limit, offset=offset
    )
    unread_count = await Notification.unread_count(db, current_user.id)
    return NotificationListResponse(
        items=[
            NotificationResponse.model_validate(notification)
            for notification in notifications
        ],
        unread_count=unread_count,
        has_more=len(notifications) == limit,
    )


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark one of the authenticated user's notifications as read",
)
async def mark_notification_read(
    notification_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> NotificationResponse:
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise NotFoundError(
            "Notification not found", code="notification_not_found"
        )
    if notification.user_id != current_user.id:
        raise ForbiddenError(
            "You can only mark your own notifications as read",
            code="not_notification_owner",
        )

    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return NotificationResponse.model_validate(notification)
