"""Focused integration tests for the services module."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_PATH = "/api/v1/auth/register"
BUSINESSES_PATH = "/api/v1/businesses"
ME_SERVICES_PATH = "/api/v1/businesses/me/services"

OWNER_A = {
    "email": "owner-a@example.com",
    "password": "password123",
    "full_name": "Owner A",
    "role": "BUSINESS_OWNER",
}
OWNER_B = {
    "email": "owner-b@example.com",
    "password": "password123",
    "full_name": "Owner B",
    "role": "BUSINESS_OWNER",
}
CUSTOMER = {
    "email": "customer@example.com",
    "password": "password123",
    "full_name": "Customer User",
    "role": "CUSTOMER",
}

BUSINESS_PAYLOAD = {
    "name": "Sunshine Salon",
    "category": "salon",
    "description": "A cozy neighborhood salon",
    "address": "1 Main Street",
    "timezone": "UTC",
}

SERVICE_PAYLOAD = {
    "name": "Haircut",
    "description": "Signature cut and style",
    "price": 25.00,
    "duration_minutes": 45,
}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, payload: dict) -> dict:
    resp = await client.post(REGISTER_PATH, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _register_owner_a(client: AsyncClient) -> dict:
    return await _register(client, OWNER_A)


async def _create_business(client: AsyncClient, token: str) -> dict:
    resp = await client.post(
        BUSINESSES_PATH, json=BUSINESS_PAYLOAD, headers=_bearer(token)
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_service(
    client: AsyncClient, token: str, *, name: str = "Haircut", **overrides
) -> dict:
    resp = await client.post(
        ME_SERVICES_PATH,
        json={**SERVICE_PAYLOAD, "name": name, **overrides},
        headers=_bearer(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_owner_creates_service(client: AsyncClient) -> None:
    owner = await _register_owner_a(client)
    business = await _create_business(client, owner["access_token"])

    body = await _create_service(client, owner["access_token"])

    assert body["id"] > 0
    assert body["business_id"] == business["id"]
    assert body["name"] == "Haircut"
    assert body["description"] == "Signature cut and style"
    assert float(body["price"]) == pytest.approx(25.00)
    assert body["duration_minutes"] == 45
    assert body["is_active"] is True


async def test_owner_lists_and_updates_services(client: AsyncClient) -> None:
    owner = await _register_owner_a(client)
    await _create_business(client, owner["access_token"])
    token = owner["access_token"]
    in_headers = _bearer(token)

    await _create_service(client, token, name="Haircut")
    await _create_service(client, token, name="Beard Trim", price=15.50, duration_minutes=20)

    listed = await client.get(ME_SERVICES_PATH, headers=in_headers)
    assert listed.status_code == 200, listed.text
    assert [row["name"] for row in listed.json()] == ["Haircut", "Beard Trim"]

    updated = await client.patch(
        f"{ME_SERVICES_PATH}/{listed.json()[0]['id']}",
        json={"name": "Haircut Deluxe", "price": 35.00, "duration_minutes": 60},
        headers=in_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Haircut Deluxe"
    assert float(updated.json()["price"]) == pytest.approx(35.00)
    assert updated.json()["duration_minutes"] == 60

    rechecked = await client.get(ME_SERVICES_PATH, headers=in_headers)
    assert [row["name"] for row in rechecked.json()] == ["Haircut Deluxe", "Beard Trim"]


async def test_duplicate_service_name_rejected(client: AsyncClient) -> None:
    owner = await _register_owner_a(client)
    await _create_business(client, owner["access_token"])
    token = owner["access_token"]
    in_headers = _bearer(token)

    first = await _create_service(client, token, name="Haircut")

    dup = await client.post(ME_SERVICES_PATH, json=SERVICE_PAYLOAD, headers=in_headers)
    assert dup.status_code == 409
    assert dup.json()["code"] == "service_already_exists"

    rename_to_dup = await client.patch(
        f"{ME_SERVICES_PATH}/{first['id']}",
        json={"name": "Haircut"},  # same name as the duplicate attempt, service itself
        headers=in_headers,
    )
    # Updating to its own name is fine; only a *different* service's name collides.
    assert rename_to_dup.status_code == 200


async def test_duplicate_service_name_on_update_rejected(
    client: AsyncClient,
) -> None:
    owner = await _register_owner_a(client)
    await _create_business(client, owner["access_token"])
    token = owner["access_token"]
    in_headers = _bearer(token)

    first = await _create_service(client, token, name="Haircut")
    second = await _create_service(client, token, name="Beard Trim")

    collide = await client.patch(
        f"{ME_SERVICES_PATH}/{second['id']}",
        json={"name": first["name"]},
        headers=in_headers,
    )
    assert collide.status_code == 409
    assert collide.json()["code"] == "service_already_exists"


async def test_invalid_price_and_duration_rejected(client: AsyncClient) -> None:
    owner = await _register_owner_a(client)
    await _create_business(client, owner["access_token"])
    headers = _bearer(owner["access_token"])

    for case in (
        {"price": -1},
        {"price": 10.999},
        {"price": 100_000_000},
        {"duration_minutes": 0},
        {"duration_minutes": 2000},
    ):
        resp = await client.post(
            ME_SERVICES_PATH, json={**SERVICE_PAYLOAD, **case}, headers=headers
        )
        assert resp.status_code == 422, (case, resp.text)


async def test_customer_cannot_manage_services(client: AsyncClient) -> None:
    customer = await _register(client, CUSTOMER)
    headers = _bearer(customer["access_token"])

    create = await client.post(ME_SERVICES_PATH, json=SERVICE_PAYLOAD, headers=headers)
    assert create.status_code == 403
    assert create.json()["code"] == "owner_required"

    listed = await client.get(ME_SERVICES_PATH, headers=headers)
    assert listed.status_code == 403
    assert listed.json()["code"] == "owner_required"

    update = await client.patch(
        f"{ME_SERVICES_PATH}/1", json={"name": "Nope"}, headers=headers
    )
    assert update.status_code == 403
    assert update.json()["code"] == "owner_required"


async def test_customer_can_view_active_services(client: AsyncClient) -> None:
    owner = await _register_owner_a(client)
    business = await _create_business(client, owner["access_token"])
    service = await _create_service(client, owner["access_token"])

    customer = await _register(client, CUSTOMER)
    resp = await client.get(
        f"{BUSINESSES_PATH}/{business['id']}/services",
        headers=_bearer(customer["access_token"]),
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["id"] == service["id"]
    assert rows[0]["name"] == "Haircut"
    assert "business_id" not in rows[0]

    missing = await client.get(
        f"{BUSINESSES_PATH}/999999999/services",
        headers=_bearer(customer["access_token"]),
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "business_not_found"


async def test_inactive_service_hidden_from_customers(client: AsyncClient) -> None:
    owner = await _register_owner_a(client)
    business = await _create_business(client, owner["access_token"])
    token = owner["access_token"]
    in_headers = _bearer(token)

    active = await _create_service(client, token, name="Haircut")
    hidden = await _create_service(client, token, name="Manicure")

    toggled = await client.patch(
        f"{ME_SERVICES_PATH}/{hidden['id']}/active",
        json={"is_active": False},
        headers=in_headers,
    )
    assert toggled.status_code == 200, toggled.text
    assert toggled.json()["is_active"] is False

    owner_list = await client.get(ME_SERVICES_PATH, headers=in_headers)
    assert len(owner_list.json()) == 2
    assert {row["id"] for row in owner_list.json()} == {active["id"], hidden["id"]}

    customer = await _register(client, CUSTOMER)
    public = await client.get(
        f"{BUSINESSES_PATH}/{business['id']}/services",
        headers=_bearer(customer["access_token"]),
    )
    assert public.status_code == 200
    assert [row["id"] for row in public.json()] == [active["id"]]

    reactivated = await client.patch(
        f"{ME_SERVICES_PATH}/{hidden['id']}/active",
        json={"is_active": True},
        headers=in_headers,
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True


async def test_cross_owner_access_rejected(client: AsyncClient) -> None:
    owner_a = await _register(client, OWNER_A)
    owner_b = await _register(client, OWNER_B)
    business_a = await _create_business(client, owner_a["access_token"])
    await _create_business(client, owner_b["access_token"])

    token_a = owner_a["access_token"]
    service_a = await _create_service(client, token_a, name="Haircut")

    token_b = owner_b["access_token"]
    headers_b = _bearer(token_b)

    update = await client.patch(
        f"{ME_SERVICES_PATH}/{service_a['id']}",
        json={"name": "Stolen"},
        headers=headers_b,
    )
    assert update.status_code == 403
    assert update.json()["code"] == "not_owner"

    toggle = await client.patch(
        f"{ME_SERVICES_PATH}/{service_a['id']}/active",
        json={"is_active": False},
        headers=headers_b,
    )
    assert toggle.status_code == 403
    assert toggle.json()["code"] == "not_owner"

    owner_a_list = await client.get(
        ME_SERVICES_PATH, headers=_bearer(token_a)
    )
    assert len(owner_a_list.json()) == 1
    assert owner_a_list.json()[0]["id"] == service_a["id"]
    assert owner_a_list.json()[0]["is_active"] is True

    owner_b_list = await client.get(ME_SERVICES_PATH, headers=headers_b)
    assert owner_b_list.json() == []

    # Owner B can still view owner A's public services.
    public = await client.get(
        f"{BUSINESSES_PATH}/{business_a['id']}/services",
        headers=_bearer(token_b),
    )
    assert public.status_code == 200
    assert [row["id"] for row in public.json()] == [service_a["id"]]