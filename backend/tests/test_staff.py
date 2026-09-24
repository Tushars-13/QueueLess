"""Focused integration tests for the staff module."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

BUSINESSES_PATH = "/api/v1/businesses"
ME_STAFF_PATH = f"{BUSINESSES_PATH}/me/staff"
REGISTER_PATH = "/api/v1/auth/register"

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

STAFF_PAYLOAD = {
    "name": "Alex",
    "title": "Senior Stylist",
}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, payload: dict) -> dict:
    resp = await client.post(REGISTER_PATH, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _register_owner(client: AsyncClient, payload: dict) -> dict:
    return await _register(client, payload)


async def _create_business(client: AsyncClient, token: str) -> dict:
    resp = await client.post(
        BUSINESSES_PATH,
        json=BUSINESS_PAYLOAD,
        headers=_bearer(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_service(client: AsyncClient, token: str, **name_overrides) -> dict:
    resp = await client.post(
        f"{BUSINESSES_PATH}/me/services",
        json={**SERVICE_PAYLOAD, "name": name_overrides.get("name", "Haircut")},
        headers=_bearer(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_staff(client: AsyncClient, token: str, **overrides) -> dict:
    resp = await client.post(
        ME_STAFF_PATH,
        json={**STAFF_PAYLOAD, **overrides},
        headers=_bearer(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _setup_owner_with_business(client: AsyncClient) -> tuple[dict, dict]:
    owner = await _register_owner(client, OWNER_A)
    business = await _create_business(client, owner["access_token"])
    return owner, business


async def test_owner_creates_staff(client: AsyncClient) -> None:
    owner, business = await _setup_owner_with_business(client)
    token = owner["access_token"]

    created = await _create_staff(client, token)

    assert created["id"] > 0
    assert created["business_id"] == business["id"]
    assert created["name"] == "Alex"
    assert created["title"] == "Senior Stylist"
    assert created["available"] is True

    duplicate = await client.post(
        ME_STAFF_PATH, json=STAFF_PAYLOAD, headers=_bearer(token)
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "staff_already_exists"


async def test_owner_lists_and_updates_staff(client: AsyncClient) -> None:
    owner, _ = await _setup_owner_with_business(client)
    token = owner["access_token"]

    await _create_staff(client, token)
    await _create_staff(client, token, name="Jordan", title="Barber")

    listed = await client.get(ME_STAFF_PATH, headers=_bearer(token))
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert [row["name"] for row in rows] == ["Alex", "Jordan"]

    updated = await client.patch(
        f"{ME_STAFF_PATH}/{rows[0]['id']}",
        json={"name": "Alexandra"},
        headers=_bearer(token),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Alexandra"

    rechecked = await client.get(ME_STAFF_PATH, headers=_bearer(token))
    assert [row["name"] for row in rechecked.json()] == ["Alexandra", "Jordan"]


async def test_owner_changes_staff_availability(client: AsyncClient) -> None:
    owner, _ = await _setup_owner_with_business(client)
    token = owner["access_token"]
    staff = await _create_staff(client, token)

    deactivated = await client.patch(
        f"{ME_STAFF_PATH}/{staff['id']}/available",
        json={"available": False},
        headers=_bearer(token),
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["available"] is False

    reactivated = await client.patch(
        f"{ME_STAFF_PATH}/{staff['id']}/available",
        json={"available": True},
        headers=_bearer(token),
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["available"] is True


async def test_owner_assigns_and_removes_staff_services(
    client: AsyncClient,
) -> None:
    owner, _ = await _setup_owner_with_business(client)
    token = owner["access_token"]
    staff = await _create_staff(client, token)

    haircut = await _create_service(client, token, name="Haircut")
    manicure = await _create_service(client, token, name="Manicure")

    first = await client.post(
        f"{ME_STAFF_PATH}/{staff['id']}/services/{haircut['id']}",
        headers=_bearer(token),
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        f"{ME_STAFF_PATH}/{staff['id']}/services/{manicure['id']}",
        headers=_bearer(token),
    )
    assert second.status_code == 200

    assigned = await client.get(
        f"{ME_STAFF_PATH}/{staff['id']}/services", headers=_bearer(token)
    )
    assert assigned.status_code == 200
    assert [row["id"] for row in assigned.json()] == [haircut["id"], manicure["id"]]

    removed = await client.delete(
        f"{ME_STAFF_PATH}/{staff['id']}/services/{manicure['id']}",
        headers=_bearer(token),
    )
    assert removed.status_code == 204

    after_remove = await client.get(
        f"{ME_STAFF_PATH}/{staff['id']}/services", headers=_bearer(token)
    )
    assert [row["id"] for row in after_remove.json()] == [haircut["id"]]


async def test_cross_business_service_assignment_rejected(
    client: AsyncClient,
) -> None:
    owner_a, _ = await _setup_owner_with_business(client)
    owner_b = await _register_owner(client, OWNER_B)
    await _create_business(client, owner_b["access_token"])

    token_a = owner_a["access_token"]
    service_a = await _create_service(client, token_a, name="Haircut")
    staff_a = await _create_staff(client, token_a)

    token_b = owner_b["access_token"]
    service_b = await _create_service(client, token_b, name="Manicure")

    foreign = await client.post(
        f"{ME_STAFF_PATH}/{staff_a['id']}/services/{service_b['id']}",
        headers=_bearer(token_b),
    )
    assert foreign.status_code == 403
    assert foreign.json()["code"] == "not_owner"

    own_assign = await client.post(
        f"{ME_STAFF_PATH}/999999/services/{service_b['id']}",
        headers=_bearer(token_b),
    )
    own_assign_status = own_assign.status_code
    assert own_assign_status in (403, 404)


async def test_customer_cannot_manage_staff(client: AsyncClient) -> None:
    customer = await _register(client, CUSTOMER)
    headers = _bearer(customer["access_token"])

    create = await client.post(ME_STAFF_PATH, json=STAFF_PAYLOAD, headers=headers)
    assert create.status_code == 403
    assert create.json()["code"] == "owner_required"

    listed = await client.get(ME_STAFF_PATH, headers=headers)
    assert listed.status_code == 403
    assert listed.json()["code"] == "owner_required"

    toggle = await client.patch(
        f"{ME_STAFF_PATH}/1/available", json={"available": False}, headers=headers
    )
    assert toggle.status_code == 403


async def test_customer_can_view_public_staff_with_availability(
    client: AsyncClient,
) -> None:
    owner, business = await _setup_owner_with_business(client)
    token = owner["access_token"]

    available_staff = await _create_staff(client, token, name="Alex")
    off_duty = await _create_staff(client, token, name="Jordan")
    await client.patch(
        f"{ME_STAFF_PATH}/{off_duty['id']}/available",
        json={"available": False},
        headers=_bearer(token),
    )

    customer = await _register(client, CUSTOMER)
    public = await client.get(
        f"{BUSINESSES_PATH}/{business['id']}/staff",
        headers=_bearer(customer["access_token"]),
    )
    assert public.status_code == 200, public.text
    rows = public.json()
    assert {row["name"] for row in rows} == {"Alex", "Jordan"}
    availability = {row["name"]: row["available"] for row in rows}
    assert availability["Alex"] is True
    assert availability["Jordan"] is False
    assert "business_id" not in rows[0]

    missing = await client.get(
        f"{BUSINESSES_PATH}/999999/staff",
        headers=_bearer(customer["access_token"]),
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "business_not_found"


async def test_cross_owner_staff_access_rejected(client: AsyncClient) -> None:
    owner_a, _ = await _setup_owner_with_business(client)
    owner_b = await _register_owner(client, OWNER_B)
    await _create_business(client, owner_b["access_token"])

    token_a = owner_a["access_token"]
    staff_a = await _create_staff(client, token_a)

    token_b = owner_b["access_token"]
    update = await client.patch(
        f"{ME_STAFF_PATH}/{staff_a['id']}",
        json={"name": "Stolen"},
        headers=_bearer(token_b),
    )
    assert update.status_code == 403
    assert update.json()["code"] == "not_owner"

    toggle = await client.patch(
        f"{ME_STAFF_PATH}/{staff_a['id']}/available",
        json={"available": False},
        headers=_bearer(token_b),
    )
    assert toggle.status_code == 403

    list_b = await client.get(ME_STAFF_PATH, headers=_bearer(token_b))
    assert list_b.status_code == 200
    assert list_b.json() == []
