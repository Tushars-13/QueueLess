"""Focused integration tests for the authentication module."""

from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token

# Run every test in the shared session event loop so SQLAlchemy's async engine
# (pooled asyncpg connections) never crosses event loops.
pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_PATH = "/api/v1/auth/register"
LOGIN_PATH = "/api/v1/auth/login"
ME_PATH = "/api/v1/auth/me"

CUSTOMER = {
    "email": "customer@example.com",
    "password": "password123",
    "full_name": "Customer User",
    "role": "CUSTOMER",
}
OWNER = {
    "email": "owner@example.com",
    "password": "password123",
    "full_name": "Owner User",
    "role": "BUSINESS_OWNER",
}


async def test_customer_registration(client: AsyncClient) -> None:
    resp = await client.post(REGISTER_PATH, json=CUSTOMER)

    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == CUSTOMER["email"]
    assert body["user"]["full_name"] == CUSTOMER["full_name"]
    assert body["user"]["role"] == "CUSTOMER"
    assert "password_hash" not in body["user"]


async def test_business_owner_registration(client: AsyncClient) -> None:
    resp = await client.post(REGISTER_PATH, json=OWNER)

    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["email"] == OWNER["email"]
    assert body["user"]["role"] == "BUSINESS_OWNER"


async def test_duplicate_email_registration_rejected(client: AsyncClient) -> None:
    await client.post(REGISTER_PATH, json=CUSTOMER)

    resp = await client.post(REGISTER_PATH, json=CUSTOMER)

    assert resp.status_code == 409
    assert resp.json()["code"] == "email_already_registered"


async def test_login_with_valid_credentials(client: AsyncClient) -> None:
    await client.post(REGISTER_PATH, json=CUSTOMER)

    resp = await client.post(
        LOGIN_PATH,
        json={"email": CUSTOMER["email"], "password": CUSTOMER["password"]},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == CUSTOMER["email"]
    assert body["user"]["role"] == "CUSTOMER"


async def test_login_with_invalid_credentials(client: AsyncClient) -> None:
    await client.post(REGISTER_PATH, json=CUSTOMER)

    wrong_password = await client.post(
        LOGIN_PATH,
        json={"email": CUSTOMER["email"], "password": "not-the-password"},
    )
    assert wrong_password.status_code == 401
    assert wrong_password.json()["code"] == "invalid_credentials"

    unknown_email = await client.post(
        LOGIN_PATH,
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert unknown_email.status_code == 401
    assert unknown_email.json()["code"] == "invalid_credentials"


async def test_authenticated_me(client: AsyncClient) -> None:
    token = (await client.post(REGISTER_PATH, json=CUSTOMER)).json()["access_token"]

    resp = await client.get(ME_PATH, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    me = resp.json()
    assert me["email"] == CUSTOMER["email"]
    assert me["full_name"] == CUSTOMER["full_name"]
    assert me["role"] == "CUSTOMER"
    assert "password_hash" not in me


async def test_me_rejects_invalid_and_expired_tokens(
    client: AsyncClient,
) -> None:
    # No token at all.
    resp = await client.get(ME_PATH)
    assert resp.status_code == 401

    # Malformed token.
    resp = await client.get(ME_PATH, headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401

    # Well-formed token for a user that does not exist.
    ghost = create_access_token(subject="999999999", role="CUSTOMER")
    resp = await client.get(ME_PATH, headers={"Authorization": f"Bearer {ghost}"})
    assert resp.status_code == 401

    # Expired token.
    expired = create_access_token(
        subject="1", role="CUSTOMER", expires_delta=timedelta(minutes=-5)
    )
    resp = await client.get(
        ME_PATH, headers={"Authorization": f"Bearer {expired}"}
    )
    assert resp.status_code == 401


async def test_role_information_in_me(client: AsyncClient) -> None:
    owner = (await client.post(REGISTER_PATH, json=OWNER)).json()
    customer = (await client.post(REGISTER_PATH, json=CUSTOMER)).json()

    owner_me = await client.get(
        ME_PATH, headers={"Authorization": f"Bearer {owner['access_token']}"}
    )
    assert owner_me.status_code == 200
    assert owner_me.json()["role"] == "BUSINESS_OWNER"

    customer_me = await client.get(
        ME_PATH, headers={"Authorization": f"Bearer {customer['access_token']}"}
    )
    assert customer_me.status_code == 200
    assert customer_me.json()["role"] == "CUSTOMER"