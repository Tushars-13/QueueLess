"""Focused integration tests for the business-owner business-profile module."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_PATH = "/api/v1/auth/register"
BUSINESSES_PATH = "/api/v1/businesses"
ME_PATH = "/api/v1/businesses/me"
ME_HOURS_PATH = "/api/v1/businesses/me/hours"

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
    "latitude": 28.613939,
    "longitude": 77.209021,
    "timezone": "UTC",
}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, payload: dict) -> dict:
    resp = await client.post(REGISTER_PATH, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _register_owner(client: AsyncClient) -> dict:
    return await _register(client, OWNER_A)


async def _create_business(client: AsyncClient, token: str) -> dict:
    resp = await client.post(BUSINESSES_PATH, json=BUSINESS_PAYLOAD, headers=_bearer(token))
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_owner_can_create_business(client: AsyncClient) -> None:
    owner = await _register_owner(client)
    body = await _create_business(client, owner["access_token"])

    assert body["id"] > 0
    assert body["owner_id"] == owner["user"]["id"]
    assert body["name"] == BUSINESS_PAYLOAD["name"]
    assert body["category"] == BUSINESS_PAYLOAD["category"]
    assert body["description"] == BUSINESS_PAYLOAD["description"]
    assert body["address"] == BUSINESS_PAYLOAD["address"]
    assert float(body["latitude"]) == pytest.approx(28.613939)
    assert float(body["longitude"]) == pytest.approx(77.209021)
    assert body["timezone"] == "UTC"
    assert body["is_active"] is True


async def test_business_cast_validation(client: AsyncClient) -> None:
    """Latitude/longitude bounds and pairing are enforced."""
    owner = await _register_owner(client)
    headers = _bearer(owner["access_token"])

    out_of_range = await client.post(
        BUSINESSES_PATH, json={**BUSINESS_PAYLOAD, "latitude": 91}, headers=headers
    )
    assert out_of_range.status_code == 422

    bad_longitude = await client.post(
        BUSINESSES_PATH, json={**BUSINESS_PAYLOAD, "longitude": -181}, headers=headers
    )
    assert bad_longitude.status_code == 422

    unpaired = await client.post(
        BUSINESSES_PATH,
        json={**BUSINESS_PAYLOAD, "longitude": None},
        headers=headers,
    )
    assert unpaired.status_code == 422


async def test_owner_can_read_and_update_own_business(
    client: AsyncClient,
) -> None:
    owner = await _register_owner(client)
    headers = _bearer(owner["access_token"])
    created = await _create_business(client, owner["access_token"])

    gotten = await client.get(ME_PATH, headers=headers)
    assert gotten.status_code == 200
    assert gotten.json()["id"] == created["id"]
    assert gotten.json()["name"] == BUSINESS_PAYLOAD["name"]

    updated = await client.patch(
        ME_PATH,
        json={"name": "Sunshine Salon Premium", "address": "99 High Street"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Sunshine Salon Premium"
    assert updated.json()["address"] == "99 High Street"
    assert updated.json()["latitude"] == created["latitude"]

    rechecked = await client.get(ME_PATH, headers=headers)
    assert rechecked.json()["name"] == "Sunshine Salon Premium"


async def test_owner_management_endpoints_remain_owner_only(
    client: AsyncClient,
) -> None:
    customer = await _register(client, CUSTOMER)
    headers = _bearer(customer["access_token"])

    create = await client.post(BUSINESSES_PATH, json=BUSINESS_PAYLOAD, headers=headers)
    assert create.status_code == 403
    assert create.json()["code"] == "owner_required"

    for method, path, payload in (
        ("get", ME_PATH, None),
        ("patch", ME_PATH, {"name": "Nope"}),
        ("get", ME_HOURS_PATH, None),
        ("put", ME_HOURS_PATH, {"hours": [{"day_of_week": 0, "is_closed": True}]}),
    ):
        resp = await client.request(method, path, json=payload, headers=headers)
        assert resp.status_code == 403, (method, path, resp.text)
        assert resp.json()["code"] == "owner_required"

    # An owner still has access to every management endpoint.
    owner = await _register_owner(client)
    owner_headers = _bearer(owner["access_token"])
    created = await _create_business(client, owner["access_token"])
    assert created["owner_id"] == owner["user"]["id"]
    for method, path, payload in (
        ("get", ME_PATH, None),
        ("get", ME_HOURS_PATH, None),
    ):
        resp = await client.request(method, path, json=payload, headers=owner_headers)
        assert resp.status_code == 200, (method, path, resp.text)


async def test_customer_can_view_business_profile(client: AsyncClient) -> None:
    owner = await _register_owner(client)
    business = await _create_business(client, owner["access_token"])

    customer = await _register(client, CUSTOMER)
    resp = await client.get(
        f"{BUSINESSES_PATH}/{business['id']}",
        headers=_bearer(customer["access_token"]),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == business["id"]
    assert body["name"] == BUSINESS_PAYLOAD["name"]
    assert body["category"] == BUSINESS_PAYLOAD["category"]
    assert "owner_id" not in body


async def test_owner_can_view_business_profile(client: AsyncClient) -> None:
    owner_a = await _register(client, OWNER_A)
    business_a = await _create_business(client, owner_a["access_token"])
    owner_b = await _register(client, OWNER_B)

    resp = await client.get(
        f"{BUSINESSES_PATH}/{business_a['id']}",
        headers=_bearer(owner_b["access_token"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == business_a["id"]
    assert resp.json()["name"] == BUSINESS_PAYLOAD["name"]


async def test_nonexistent_business_returns_404(client: AsyncClient) -> None:
    customer = await _register(client, CUSTOMER)
    resp = await client.get(
        f"{BUSINESSES_PATH}/999999999", headers=_bearer(customer["access_token"])
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "business_not_found"


async def test_duplicate_business_creation_rejected(client: AsyncClient) -> None:
    owner = await _register_owner(client)
    await _create_business(client, owner["access_token"])

    again = await client.post(
        BUSINESSES_PATH, json=BUSINESS_PAYLOAD, headers=_bearer(owner["access_token"])
    )
    assert again.status_code == 409
    assert again.json()["code"] == "business_already_exists"


async def test_opening_hours_roundtrip_and_validation(
    client: AsyncClient,
) -> None:
    owner = await _register_owner(client)
    headers = _bearer(owner["access_token"])
    await _create_business(client, owner["access_token"])

    full_week = [
        {"day_of_week": day, "open_time": "09:00:00", "close_time": "17:00:00"}
        for day in range(7)
    ]
    saved = await client.put(ME_HOURS_PATH, json={"hours": full_week}, headers=headers)
    assert saved.status_code == 200, saved.text
    assert len(saved.json()) == 7
    assert [row["day_of_week"] for row in saved.json()] == list(range(7))
    assert saved.json()[3]["open_time"] == "09:00:00"

    fetched = await client.get(ME_HOURS_PATH, headers=headers)
    assert fetched.status_code == 200
    assert len(fetched.json()) == 7

    # A closed day must not carry times.
    closed_with_times = await client.put(
        ME_HOURS_PATH,
        json={
            "hours": [
                {"day_of_week": 0, "is_closed": True, "open_time": "09:00:00"}
            ]
        },
        headers=headers,
    )
    assert closed_with_times.status_code == 422

    # Open days need both times.
    missing_close = await client.put(
        ME_HOURS_PATH,
        json={"hours": [{"day_of_week": 0, "open_time": "09:00:00"}]},
        headers=headers,
    )
    assert missing_close.status_code == 422

    # close_time must be after open_time.
    inverted = await client.put(
        ME_HOURS_PATH,
        json={
            "hours": [{"day_of_week": 0, "open_time": "17:00:00", "close_time": "09:00:00"}]
        },
        headers=headers,
    )
    assert inverted.status_code == 422

    # Duplicate weekdays are rejected.
    duplicates = await client.put(
        ME_HOURS_PATH,
        json={
            "hours": [
                {"day_of_week": 0, "open_time": "09:00:00", "close_time": "17:00:00"},
                {"day_of_week": 0, "open_time": "10:00:00", "close_time": "18:00:00"},
            ]
        },
        headers=headers,
    )
    assert duplicates.status_code == 422

    # Weekday out of range.
    out_of_range = await client.put(
        ME_HOURS_PATH,
        json={"hours": [{"day_of_week": 7, "open_time": "09:00:00", "close_time": "17:00:00"}]},
        headers=headers,
    )
    assert out_of_range.status_code == 422

    # Empty schedule is rejected.
    empty = await client.put(ME_HOURS_PATH, json={"hours": []}, headers=headers)
    assert empty.status_code == 422

    # A valid closed-only schedule still works.
    closed_week = [
        {"day_of_week": day, "is_closed": True} for day in range(7)
    ]
    replaced = await client.put(ME_HOURS_PATH, json={"hours": closed_week}, headers=headers)
    assert replaced.status_code == 200
    assert all(row["is_closed"] for row in replaced.json())