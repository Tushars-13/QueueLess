"""Authentication endpoints: registration, login, and current user."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLogin
from app.schemas.user import UserRegister, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _build_token_response(user: User) -> TokenResponse:
    token = create_access_token(subject=str(user.id), role=str(user.role.value))
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a customer or business owner account",
)
async def register(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Create a new user and return a JWT access token for it."""
    email = _normalize_email(str(payload.email))

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError(
            "An account with this email already exists",
            code="email_already_registered",
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        phone=payload.phone,
        role=payload.role,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # Race: another request created the same email between check and insert.
        await db.rollback()
        raise ConflictError(
            "An account with this email already exists",
            code="email_already_registered",
        ) from None

    await db.refresh(user)
    return _build_token_response(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange credentials for a JWT access token",
)
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Authenticate against email + password and return a JWT access token."""
    email = _normalize_email(str(payload.email))

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthenticationError(
            "Incorrect email or password",
            code="invalid_credentials",
        )

    return _build_token_response(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the authenticated user's profile",
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    """Return the profile (with role) of the current bearer-token user."""
    return UserResponse.model_validate(current_user)