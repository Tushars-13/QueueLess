"""Focused integration tests for the business-owner business-profile module."""

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.db.session import async_session_factory
from app.models.business import Business

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
OWNER_C = {
    "email": "owner-c@example.com",
    "password": "password123",
    "full_name": "Owner C",
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


async def _create_business_with(
    client: AsyncClient, owner_payload: dict, **overrides
) -> dict:
    """Create a business for a fresh owner, overriding BUSINESS_PAYLOAD fields."""
    owner = await _register(client, owner_payload)
    payload = {**BUSINESS_PAYLOAD, **overrides}
    resp = await client.post(
        BUSINESSES_PATH, json=payload, headers=_bearer(owner["access_token"])
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _set_business_active(business_id: int, is_active: bool) -> None:
    """Toggle is_active directly; the owner API deliberately cannot change it."""
    async with async_session_factory() as session:
        await session.execute(
            update(Business).where(Business.id == business_id).values(is_active=is_active)
        )
        await session.commit()


async def _discover(client: AsyncClient, token: str, **params) -> dict:
    resp = await client.get(
        BUSINESSES_PATH, params=params, headers=_bearer(token)
    )
    assert resp.status_code == 200, resp.text
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


# --- customer discovery (GET /businesses) ----------------------------------


async def test_discovery_requires_authentication(client: AsyncClient) -> None:
    resp = await client.get(BUSINESSES_PATH)

    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "missing_token"


async def test_discovery_is_empty_when_no_business_exists(
    client: AsyncClient,
) -> None:
    customer = await _register(client, CUSTOMER)

    body = await _discover(client, customer["access_token"])

    assert body["items"] == []
    assert body["has_more"] is False


async def test_discovery_returns_active_businesses(client: AsyncClient) -> None:
    created = await _create_business_with(
        client, OWNER_A, name="Sunshine Salon", category="salon"
    )
    customer = await _register(client, CUSTOMER)

    body = await _discover(client, customer["access_token"])

    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == created["id"]
    assert item["name"] == "Sunshine Salon"
    assert item["category"] == "salon"
    assert item["is_active"] is True


async def test_discovery_excludes_inactive_businesses(client: AsyncClient) -> None:
    created = await _create_business_with(client, OWNER_A, name="Closed Shop")
    await _set_business_active(created["id"], False)
    customer = await _register(client, CUSTOMER)

    body = await _discover(client, customer["access_token"])

    assert [item["id"] for item in body["items"]] == []


async def test_discovery_allows_business_owners_too(client: AsyncClient) -> None:
    created = await _create_business_with(client, OWNER_A, name="Sunshine Salon")
    other_owner = await _register(client, OWNER_B)

    body = await _discover(client, other_owner["access_token"])

    assert [item["id"] for item in body["items"]] == [created["id"]]


async def test_discovery_q_matches_name_substring_case_insensitively(
    client: AsyncClient,
) -> None:
    created = await _create_business_with(client, OWNER_A, name="Sunshine Salon")
    await _create_business_with(client, OWNER_B, name="City Clinic")
    customer = await _register(client, CUSTOMER)
    token = customer["access_token"]

    lower = await _discover(client, token, q="sunshine")
    upper = await _discover(client, token, q="SUNSHINE")
    middle = await _discover(client, token, q="Shine Sal")

    assert [item["id"] for item in lower["items"]] == [created["id"]]
    assert [item["id"] for item in upper["items"]] == [created["id"]]
    assert [item["id"] for item in middle["items"]] == [created["id"]]


async def test_discovery_q_searches_name_only(client: AsyncClient) -> None:
    await _create_business_with(
        client,
        OWNER_A,
        name="Sunshine Salon",
        description="A cozy neighborhood salon",
        address="1 Main Street",
        category="salon",
    )
    customer = await _register(client, CUSTOMER)
    token = customer["access_token"]

    # "neighborhood" only appears in the description.
    from_description = await _discover(client, token, q="neighborhood")
    from_address = await _discover(client, token, q="Main Street")

    assert from_description["items"] == []
    assert from_address["items"] == []


async def test_discovery_q_treats_sql_wildcards_literally(client: AsyncClient) -> None:
    await _create_business_with(client, OWNER_A, name="Sunshine Salon")
    customer = await _register(client, CUSTOMER)

    everything = await _discover(client, customer["access_token"], q="%")
    underscore = await _discover(client, customer["access_token"], q="_unshine")

    assert everything["items"] == []
    assert underscore["items"] == []


async def test_discovery_filters_by_category_exactly(client: AsyncClient) -> None:
    salon = await _create_business_with(client, OWNER_A, category="salon")
    await _create_business_with(client, OWNER_B, category="clinic")
    customer = await _register(client, CUSTOMER)
    token = customer["access_token"]

    exact = await _discover(client, token, category="salon")
    prefix = await _discover(client, token, category="salo")

    assert [item["id"] for item in exact["items"]] == [salon["id"]]
    assert prefix["items"] == []


async def test_discovery_nearby_uses_a_bounding_box(client: AsyncClient) -> None:
    centre = await _create_business_with(
        client,
        OWNER_A,
        name="Centre Shop",
        latitude=28.613939,
        longitude=77.209021,
    )
    # Inside the 0.1-degree box on both axes.
    corner = await _create_business_with(
        client,
        OWNER_B,
        name="Corner Shop",
        latitude=28.65,
        longitude=77.25,
    )
    # Outside on latitude only.
    await _create_business_with(
        client,
        OWNER_C,
        name="Far Shop",
        latitude=28.80,
        longitude=77.209021,
    )
    customer = await _register(client, CUSTOMER)

    body = await _discover(
        client, customer["access_token"], latitude=28.613939, longitude=77.209021
    )

    assert sorted(item["id"] for item in body["items"]) == sorted(
        [centre["id"], corner["id"]]
    )


async def test_discovery_rejects_latitude_without_longitude(
    client: AsyncClient,
) -> None:
    customer = await _register(client, CUSTOMER)

    resp = await client.get(
        BUSINESSES_PATH,
        params={"latitude": 28.613939},
        headers=_bearer(customer["access_token"]),
    )

    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "validation_error"


async def test_discovery_rejects_longitude_without_latitude(
    client: AsyncClient,
) -> None:
    customer = await _register(client, CUSTOMER)

    resp = await client.get(
        BUSINESSES_PATH,
        params={"longitude": 77.209021},
        headers=_bearer(customer["access_token"]),
    )

    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "validation_error"


async def test_discovery_combines_all_filters(client: AsyncClient) -> None:
    wanted = await _create_business_with(
        client,
        OWNER_A,
        name="Sunshine Salon",
        category="salon",
        latitude=28.613939,
        longitude=77.209021,
    )
    # Right name and category, wrong location.
    await _create_business_with(
        client,
        OWNER_B,
        name="Sunshine Spa",
        category="salon",
        latitude=10.0,
        longitude=10.0,
    )
    # Right name and location, wrong category.
    await _create_business_with(
        client,
        OWNER_C,
        name="Sunshine Clinic",
        category="clinic",
        latitude=28.613939,
        longitude=77.209021,
    )
    customer = await _register(client, CUSTOMER)

    body = await _discover(
        client,
        customer["access_token"],
        q="sunshine",
        category="salon",
        latitude=28.613939,
        longitude=77.209021,
    )

    assert [item["id"] for item in body["items"]] == [wanted["id"]]


async def test_discovery_paginates_with_limit_and_offset(client: AsyncClient) -> None:
    first = await _create_business_with(client, OWNER_A, name="Alpha")
    second = await _create_business_with(client, OWNER_B, name="Beta")
    third = await _create_business_with(client, OWNER_C, name="Gamma")
    customer = await _register(client, CUSTOMER)
    token = customer["access_token"]

    page_one = await _discover(client, token, limit=2, offset=0)
    page_two = await _discover(client, token, limit=2, offset=2)

    assert [item["id"] for item in page_one["items"]] == [first["id"], second["id"]]
    assert [item["id"] for item in page_two["items"]] == [third["id"]]


async def test_discovery_validates_pagination_bounds(client: AsyncClient) -> None:
    customer = await _register(client, CUSTOMER)
    headers = _bearer(customer["access_token"])

    zero_limit = await client.get(BUSINESSES_PATH, params={"limit": 0}, headers=headers)
    huge_limit = await client.get(BUSINESSES_PATH, params={"limit": 101}, headers=headers)
    negative_offset = await client.get(
        BUSINESSES_PATH, params={"offset": -1}, headers=headers
    )

    assert zero_limit.status_code == 422
    assert huge_limit.status_code == 422
    assert negative_offset.status_code == 422


async def test_discovery_orders_deterministically_by_id(client: AsyncClient) -> None:
    created = [
        await _create_business_with(client, payload, name=f"Shop {index}")
        for index, payload in enumerate((OWNER_A, OWNER_B, OWNER_C), start=1)
    ]
    customer = await _register(client, CUSTOMER)
    token = customer["access_token"]

    first_read = await _discover(client, token)
    second_read = await _discover(client, token)

    expected = sorted(business["id"] for business in created)
    assert [item["id"] for item in first_read["items"]] == expected
    assert [item["id"] for item in second_read["items"]] == expected


async def test_discovery_has_more_reflects_a_following_page(
    client: AsyncClient,
) -> None:
    await _create_business_with(client, OWNER_A, name="Alpha")
    await _create_business_with(client, OWNER_B, name="Beta")
    customer = await _register(client, CUSTOMER)
    token = customer["access_token"]

    exact_fit = await _discover(client, token, limit=2)
    smaller_page = await _discover(client, token, limit=5)
    more_available = await _discover(client, token, limit=1)

    assert len(exact_fit["items"]) == 2
    assert exact_fit["has_more"] is True
    assert smaller_page["has_more"] is False
    assert more_available["has_more"] is True


async def test_discovery_items_do_not_expose_owner_id(client: AsyncClient) -> None:
    await _create_business_with(client, OWNER_A, name="Sunshine Salon")
    customer = await _register(client, CUSTOMER)

    body = await _discover(client, customer["access_token"])

    assert set(body) == {"items", "has_more"}
    assert "owner_id" not in body["items"][0]
    assert set(body["items"][0]) == {
        "id",
        "name",
        "category",
        "description",
        "address",
        "latitude",
        "longitude",
        "timezone",
        "is_active",
        "created_at",
        "updated_at",
    }
