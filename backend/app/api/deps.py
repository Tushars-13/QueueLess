"""Shared API dependencies."""

from typing import Annotated, Any

import jwt as pyjwt
from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ForbiddenError
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(message: str, *, code: str) -> None:
    raise AuthenticationError(message, code=code)


def _extract_user_id(payload: dict[str, Any]) -> int:
    subject = payload.get("sub")
    if subject is None:
        _unauthorized("Invalid access token", code="invalid_token")
    try:
        return int(subject)
    except (TypeError, ValueError):
        _unauthorized("Invalid access token", code="invalid_token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Validate the bearer token and return the authenticated user (or 401)."""
    if credentials is None:
        _unauthorized("Authentication required", code="missing_token")

    try:
        payload = decode_access_token(credentials.credentials)
    except pyjwt.ExpiredSignatureError:
        _unauthorized("Access token has expired", code="expired_token")
    except pyjwt.InvalidTokenError:
        _unauthorized("Invalid access token", code="invalid_token")

    user_id = _extract_user_id(payload)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        _unauthorized("Invalid access token", code="invalid_token")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_owner(current_user: CurrentUser) -> User:
    """Require an authenticated user with the BUSINESS_OWNER role."""
    if current_user.role != UserRole.BUSINESS_OWNER:
        raise ForbiddenError(
            "Only business owners can access business endpoints",
            code="owner_required",
        )
    return current_user


CurrentOwner = Annotated[User, Depends(get_current_owner)]