"""Authentication (login / token) schemas."""

from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse


class UserLogin(BaseModel):
    """Credentials for the login endpoint."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT access token plus the authenticated user."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse