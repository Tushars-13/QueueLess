import asyncio
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.api.routes import queue as queue_route
from app.db.session import async_session_factory
from app.models.daily_queue import DailyQueue
from app.models.enums import QueueEntryStatus
from app.models.queue_entry import QueueEntry
from app.models.queue_event import QueueEvent

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_PATH = "/api/v1/auth/register"
BUSINESSES_PATH = "/api/v1/businesses"
ME_SERVICES_PATH = "/api/v1/businesses/me/services"
ME_STAFF_PATH = "/api/v1/businesses/me/staff"
ME_QUEUE_PATH = "/api/v1/businesses/me/queue"
CLOSE_QUEUE_PATH = "/api/v1/businesses/me/queue/close"

OWNER_A = {
    "email": "queue-owner-a@example.com",
    "password": "password123",
    "full_name": "Queue Owner A",
    "role": "BUSINESS_OWNER",
}
OWNER_B = {
    "email": "queue-owner-b@example.com",
    "password": "password123",
    "full_name": "Queue Owner B",
    "role": "BUSINESS_OWNER",
}
CUSTOMER_A = {
    "email": "queue-customer-a@example.com",
    "password": "password123",
    "full_name": "Queue Customer A",
    "role": "CUSTOMER",
}
CUSTOMER_B = {
    "email": "queue-customer-b@example.com",
    "password": "password123",
    "full_name": "Queue Customer B",
    "role": "CUSTOMER",
}
CUSTOMER_C = {
    "email": "queue-customer-c@example.com",
    "password": "password123",
    "full_name": "Queue Customer C",
    "role": "CUSTOMER",
}
CUSTOMER_D = {
    "email": "queue-customer-d@example.com",
    "password": "password123",
    "full_name": "Queue Customer D",
    "role": "CUSTOMER",
}
CUSTOMER_E = {
    "email": "queue-customer-e@example.com",
    "password": "password123",
    "full_name": "Queue Customer E",
    "role": "CUSTOMER",
}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, payload: dict) -> dict:
    response = await client.post(REGISTER_PATH, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _create_business(
    client: AsyncClient,
    token: str,
    *,
    name: str = "Queue Salon",
    timezone_name: str = "UTC",
) -> dict:
    response = await client.post(
        BUSINESSES_PATH,
        json={"name": name, "category": "salon", "timezone": timezone_name},
        headers=_bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_service(
    client: AsyncClient, token: str, *, name: str = "Haircut"
) -> dict:
    response = await client.post(
        ME_SERVICES_PATH,
        json={"name": name, "duration_minutes": 30},
        headers=_bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_staff(
    client: AsyncClient, token: str, *, name: str = "Alex"
) -> dict:
    response = await client.post(
        ME_STAFF_PATH,
        json={"name": name},
        headers=_bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _assign_staff_service(
    client: AsyncClient, token: str, staff_id: int, service_id: int
) -> None:
    response = await client.post(
        f"{ME_STAFF_PATH}/{staff_id}/services/{service_id}",
        headers=_bearer(token),
    )
    assert response.status_code == 200, response.text


async def _open_queue(client: AsyncClient, token: str) -> dict:
    response = await client.post(ME_QUEUE_PATH, headers=_bearer(token))
    assert response.status_code == 201, response.text
    return response.json()


async def _close_queue(client: AsyncClient, token: str) -> dict:
    response = await client.post(CLOSE_QUEUE_PATH, headers=_bearer(token))
    assert response.status_code == 200, response.text
    return response.json()


async def _join_queue(
    client: AsyncClient,
    business_id: int,
    token: str,
    service_id: int,
    *,
    staff_id: int | None = None,
) -> dict:
    response = await client.post(
        f"{BUSINESSES_PATH}/{business_id}/queue",
        json={"service_id": service_id, "staff_id": staff_id},
        headers=_bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _accept_entry(client: AsyncClient, token: str, entry_id: int) -> dict:
    response = await client.post(
        f"{ME_QUEUE_PATH}/entries/{entry_id}/accept", headers=_bearer(token)
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _reject_entry(client: AsyncClient, token: str, entry_id: int) -> dict:
    response = await client.post(
        f"{ME_QUEUE_PATH}/entries/{entry_id}/reject", headers=_bearer(token)
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _entry_snapshot(entry_id: int) -> dict:
    async with async_session_factory() as session:
        result = await session.execute(
            select(QueueEntry).where(QueueEntry.id == entry_id)
        )
        entry = result.scalar_one()
        return {
            "id": entry.id,
            "status": entry.status,
            "token_number": entry.token_number,
            "accepted_at": entry.accepted_at,
        }


async def _queue_snapshot(queue_id: int) -> dict:
    async with async_session_factory() as session:
        result = await session.execute(
            select(DailyQueue).where(DailyQueue.id == queue_id)
        )
        queue = result.scalar_one()
        return {
            "id": queue.id,
            "queue_date": queue.queue_date,
            "status": queue.status,
            "last_token": queue.last_token,
        }


async def _event_snapshot(entry_id: int) -> list[tuple[str | None, str, int | None]]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(QueueEvent)
            .where(QueueEvent.queue_entry_id == entry_id)
            .order_by(QueueEvent.id)
        )
        return [
            (
                event.from_status.value if event.from_status else None,
                event.to_status.value,
                event.actor_id,
            )
            for event in result.scalars()
        ]


async def _setup_business_with_service(
    client: AsyncClient,
    *,
    owner_payload: dict = OWNER_A,
    business_name: str = "Queue Salon",
    timezone_name: str = "UTC",
) -> tuple[dict, dict, dict]:
    owner = await _register(client, owner_payload)
    business = await _create_business(
        client,
        owner["access_token"],
        name=business_name,
        timezone_name=timezone_name,
    )
    service = await _create_service(client, owner["access_token"])
    return owner, business, service


async def test_daily_queue_uses_business_local_date(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_datetime = datetime
    timezone_name = "America/Los_Angeles"

    class FixedDateTime:
        @classmethod
        def now(cls, tz=None):
            value = real_datetime(2026, 1, 2, 0, 30, tzinfo=timezone.utc)
            return value.astimezone(tz) if tz is not None else value

    monkeypatch.setattr(queue_route, "datetime", FixedDateTime)
    owner, business, _service = await _setup_business_with_service(
        client, timezone_name=timezone_name
    )

    opened = await _open_queue(client, owner["access_token"])

    assert opened["queue_date"] == "2026-01-01"
    assert opened["status"] == "OPEN"
    assert opened["business_id"] == business["id"]


async def test_business_timezone_must_be_valid(client: AsyncClient) -> None:
    owner = await _register(client, OWNER_A)
    headers = _bearer(owner["access_token"])

    created = await client.post(
        BUSINESSES_PATH,
        json={"name": "Invalid Zone", "category": "salon", "timezone": "Not/AZone"},
        headers=headers,
    )
    assert created.status_code == 422, created.text

    business = await _create_business(
        client,
        owner["access_token"],
        name="Valid Zone",
    )
    updated = await client.patch(
        "/api/v1/businesses/me",
        json={"timezone": "Not/AZone"},
        headers=headers,
    )

    assert updated.status_code == 422, updated.text
    assert updated.json()["code"] == "validation_error"
    assert business["timezone"] == "UTC"


async def test_open_daily_queue_is_idempotent(client: AsyncClient) -> None:
    owner, business, _service = await _setup_business_with_service(client)
    headers = _bearer(owner["access_token"])

    first = await _open_queue(client, owner["access_token"])
    second = await client.post(ME_QUEUE_PATH, headers=headers)

    assert second.status_code == 201, second.text
    assert second.json()["id"] == first["id"]
    assert second.json()["queue_date"] == first["queue_date"]

    async with async_session_factory() as session:
        result = await session.execute(
            select(DailyQueue).where(DailyQueue.business_id == business["id"])
        )
        assert len(result.scalars().all()) == 1


async def test_closed_queue_cannot_be_reopened(client: AsyncClient) -> None:
    owner, _business, _service = await _setup_business_with_service(client)
    opened = await _open_queue(client, owner["access_token"])
    await _close_queue(client, owner["access_token"])

    response = await client.post(
        ME_QUEUE_PATH, headers=_bearer(owner["access_token"])
    )

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "queue_closed"
    snapshot = await _queue_snapshot(opened["id"])
    assert snapshot["status"] == "CLOSED"
    assert snapshot["last_token"] == 0


async def test_owner_can_view_today_queue(client: AsyncClient) -> None:
    owner, business, service = await _setup_business_with_service(client)
    customer_a = await _register(client, CUSTOMER_A)
    customer_b = await _register(client, CUSTOMER_B)
    opened = await _open_queue(client, owner["access_token"])
    first = await _join_queue(
        client, business["id"], customer_a["access_token"], service["id"]
    )
    second = await _join_queue(
        client, business["id"], customer_b["access_token"], service["id"]
    )
    await _accept_entry(client, owner["access_token"], first["id"])

    response = await client.get(
        ME_QUEUE_PATH, headers=_bearer(owner["access_token"])
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == opened["id"]
    assert body["last_token"] == 1
    assert body["total_entries"] == 2
    assert [entry["id"] for entry in body["entries"]] == [first["id"], second["id"]]
    assert [entry["status"] for entry in body["entries"]] == ["ACCEPTED", "REQUESTED"]
    assert [entry["position"] for entry in body["entries"]] == [1, None]

    closed = await _close_queue(client, owner["access_token"])
    assert closed["status"] == "CLOSED"
    assert closed["last_token"] == 1
    assert closed["total_entries"] == 2
    assert len(closed["entries"]) == 2


async def test_positions_are_scoped_to_staff_and_general_queues(
    client: AsyncClient,
) -> None:
    owner, business, service = await _setup_business_with_service(client)
    staff_a = await _create_staff(client, owner["access_token"], name="Staff A")
    staff_b = await _create_staff(client, owner["access_token"], name="Staff B")
    await _assign_staff_service(
        client, owner["access_token"], staff_a["id"], service["id"]
    )
    await _assign_staff_service(
        client, owner["access_token"], staff_b["id"], service["id"]
    )
    customers = [
        await _register(client, CUSTOMER_A),
        await _register(client, CUSTOMER_B),
        await _register(client, CUSTOMER_C),
        await _register(client, CUSTOMER_D),
        await _register(client, CUSTOMER_E),
    ]
    await _open_queue(client, owner["access_token"])

    entries = [
        await _join_queue(
            client,
            business["id"],
            customers[0]["access_token"],
            service["id"],
            staff_id=staff_a["id"],
        ),
        await _join_queue(
            client,
            business["id"],
            customers[1]["access_token"],
            service["id"],
            staff_id=staff_a["id"],
        ),
        await _join_queue(
            client,
            business["id"],
            customers[2]["access_token"],
            service["id"],
            staff_id=staff_b["id"],
        ),
        await _join_queue(
            client,
            business["id"],
            customers[3]["access_token"],
            service["id"],
            staff_id=staff_b["id"],
        ),
        await _join_queue(
            client, business["id"], customers[4]["access_token"], service["id"]
        ),
    ]
    for entry in entries:
        await _accept_entry(client, owner["access_token"], entry["id"])

    response = await client.get(
        ME_QUEUE_PATH, headers=_bearer(owner["access_token"])
    )

    assert response.status_code == 200, response.text
    positions = {
        entry["id"]: entry["position"] for entry in response.json()["entries"]
    }
    assert positions == {
        entries[0]["id"]: 1,
        entries[1]["id"]: 2,
        entries[2]["id"]: 1,
        entries[3]["id"]: 2,
        entries[4]["id"]: 1,
    }


async def test_customer_request_creates_entry_and_initial_event(
    client: AsyncClient,
) -> None:
    owner, business, service = await _setup_business_with_service(client)
    customer = await _register(client, CUSTOMER_A)
    await _open_queue(client, owner["access_token"])

    entry = await _join_queue(
        client, business["id"], customer["access_token"], service["id"]
    )

    assert entry["status"] == "REQUESTED"
    assert entry["staff_id"] is None
    assert entry["token_number"] is None
    assert entry["accepted_at"] is None
    assert entry["position"] is None

    events = await _event_snapshot(entry["id"])
    assert events == [(None, QueueEntryStatus.REQUESTED.value, customer["user"]["id"])]


async def test_business_owner_cannot_submit_customer_request(
    client: AsyncClient,
) -> None:
    owner, business, service = await _setup_business_with_service(client)
    await _open_queue(client, owner["access_token"])

    response = await client.post(
        f"{BUSINESSES_PATH}/{business['id']}/queue",
        json={"service_id": service["id"]},
        headers=_bearer(owner["access_token"]),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "customer_required"


async def test_customer_request_accepts_specific_staff(client: AsyncClient) -> None:
    owner, business, service = await _setup_business_with_service(client)
    staff = await _create_staff(client, owner["access_token"])
    await _assign_staff_service(
        client, owner["access_token"], staff["id"], service["id"]
    )
    customer = await _register(client, CUSTOMER_A)
    await _open_queue(client, owner["access_token"])

    entry = await _join_queue(
        client,
        business["id"],
        customer["access_token"],
        service["id"],
        staff_id=staff["id"],
    )

    assert entry["staff_id"] == staff["id"]


async def test_closed_queue_rejects_customer_request(client: AsyncClient) -> None:
    owner, business, service = await _setup_business_with_service(client)
    customer = await _register(client, CUSTOMER_A)
    await _open_queue(client, owner["access_token"])
    await _close_queue(client, owner["access_token"])

    response = await client.post(
        f"{BUSINESSES_PATH}/{business['id']}/queue",
        json={"service_id": service["id"]},
        headers=_bearer(customer["access_token"]),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "queue_closed"


async def test_inactive_service_rejected(client: AsyncClient) -> None:
    owner, business, service = await _setup_business_with_service(client)
    customer = await _register(client, CUSTOMER_A)
    await _open_queue(client, owner["access_token"])
    response = await client.patch(
        f"{ME_SERVICES_PATH}/{service['id']}/active",
        json={"is_active": False},
        headers=_bearer(owner["access_token"]),
    )
    assert response.status_code == 200, response.text

    rejected = await client.post(
        f"{BUSINESSES_PATH}/{business['id']}/queue",
        json={"service_id": service["id"]},
        headers=_bearer(customer["access_token"]),
    )

    assert rejected.status_code == 404
    assert rejected.json()["code"] == "service_not_found"


async def test_cross_business_service_rejected(client: AsyncClient) -> None:
    owner_a, business_a, _service_a = await _setup_business_with_service(
        client, owner_payload=OWNER_A, business_name="Queue Salon A"
    )
    owner_b, _business_b, service_b = await _setup_business_with_service(
        client, owner_payload=OWNER_B, business_name="Queue Salon B"
    )
    customer = await _register(client, CUSTOMER_A)
    await _open_queue(client, owner_a["access_token"])

    rejected = await client.post(
        f"{BUSINESSES_PATH}/{business_a['id']}/queue",
        json={"service_id": service_b["id"]},
        headers=_bearer(customer["access_token"]),
    )

    assert rejected.status_code == 404
    assert rejected.json()["code"] == "service_not_found"


async def test_invalid_and_cross_business_staff_rejected(client: AsyncClient) -> None:
    owner_a, business_a, service_a = await _setup_business_with_service(
        client, owner_payload=OWNER_A, business_name="Queue Salon A"
    )
    owner_b, _business_b, _service_b = await _setup_business_with_service(
        client, owner_payload=OWNER_B, business_name="Queue Salon B"
    )
    staff_a = await _create_staff(
        client, owner_a["access_token"], name="Unassigned Staff"
    )
    staff_b = await _create_staff(
        client, owner_b["access_token"], name="Foreign Staff"
    )
    await _open_queue(client, owner_a["access_token"])

    customer_a = await _register(client, CUSTOMER_A)
    invalid = await client.post(
        f"{BUSINESSES_PATH}/{business_a['id']}/queue",
        json={"service_id": service_a["id"], "staff_id": 999999999},
        headers=_bearer(customer_a["access_token"]),
    )
    customer_b = await _register(client, CUSTOMER_B)
    cross_business = await client.post(
        f"{BUSINESSES_PATH}/{business_a['id']}/queue",
        json={"service_id": service_a["id"], "staff_id": staff_b["id"]},
        headers=_bearer(customer_b["access_token"]),
    )
    customer_c = await _register(client, CUSTOMER_C)
    does_not_provide = await client.post(
        f"{BUSINESSES_PATH}/{business_a['id']}/queue",
        json={"service_id": service_a["id"], "staff_id": staff_a["id"]},
        headers=_bearer(customer_c["access_token"]),
    )

    assert invalid.status_code == 404
    assert invalid.json()["code"] == "staff_not_found"
    assert cross_business.status_code == 404
    assert cross_business.json()["code"] == "staff_not_found"
    assert does_not_provide.status_code == 403
    assert does_not_provide.json()["code"] == "staff_does_not_provide_service"


async def test_inactive_staff_rejected(client: AsyncClient) -> None:
    owner, business, service = await _setup_business_with_service(client)
    staff = await _create_staff(client, owner["access_token"])
    await _assign_staff_service(
        client, owner["access_token"], staff["id"], service["id"]
    )
    response = await client.patch(
        f"{ME_STAFF_PATH}/{staff['id']}/available",
        json={"available": False},
        headers=_bearer(owner["access_token"]),
    )
    assert response.status_code == 200, response.text
    customer = await _register(client, CUSTOMER_A)
    await _open_queue(client, owner["access_token"])

    rejected = await client.post(
        f"{BUSINESSES_PATH}/{business['id']}/queue",
        json={"service_id": service["id"], "staff_id": staff["id"]},
        headers=_bearer(customer["access_token"]),
    )

    assert rejected.status_code == 404
    assert rejected.json()["code"] == "staff_not_found"


async def test_duplicate_active_customer_rejected(client: AsyncClient) -> None:
    owner, business, service = await _setup_business_with_service(client)
    customer = await _register(client, CUSTOMER_A)
    await _open_queue(client, owner["access_token"])
    await _join_queue(client, business["id"], customer["access_token"], service["id"])

    duplicate = await client.post(
        f"{BUSINESSES_PATH}/{business['id']}/queue",
        json={"service_id": service["id"]},
        headers=_bearer(customer["access_token"]),
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "already_in_queue"


async def test_concurrent_duplicate_customer_requests_have_one_winner(
    client: AsyncClient,
) -> None:
    owner, business, service = await _setup_business_with_service(client)
    customer = await _register(client, CUSTOMER_A)
    await _open_queue(client, owner["access_token"])
    path = f"{BUSINESSES_PATH}/{business['id']}/queue"
    headers = _bearer(customer["access_token"])
    payload = {"service_id": service["id"], "staff_id": None}

    responses = await asyncio.wait_for(
        asyncio.gather(
            client.post(path, json=payload, headers=headers),
            client.post(path, json=payload, headers=headers),
        ),
        timeout=15,
    )

    assert sorted(response.status_code for response in responses) == [201, 409]
    async with async_session_factory() as session:
        result = await session.execute(
            select(QueueEntry).where(
                QueueEntry.customer_id == customer["user"]["id"]
            )
        )
        assert len(result.scalars().all()) == 1


async def test_owner_accept_sets_token_and_accepted_at(client: AsyncClient) -> None:
    owner, business, service = await _setup_business_with_service(client)
    customer = await _register(client, CUSTOMER_A)
    opened = await _open_queue(client, owner["access_token"])
    entry = await _join_queue(client, business["id"], customer["access_token"], service["id"])

    accepted = await _accept_entry(client, owner["access_token"], entry["id"])
    snapshot = await _entry_snapshot(entry["id"])
    queue = await _queue_snapshot(opened["id"])

    assert accepted["status"] == "ACCEPTED"
    assert accepted["token_number"] == 1
    assert accepted["accepted_at"] is not None
    assert accepted["position"] == 1
    assert snapshot["status"] == QueueEntryStatus.ACCEPTED
    assert snapshot["token_number"] == 1
    assert snapshot["accepted_at"] is not None
    assert queue["last_token"] == 1
    assert await _event_snapshot(entry["id"]) == [
        (None, QueueEntryStatus.REQUESTED.value, customer["user"]["id"]),
        (
            QueueEntryStatus.REQUESTED.value,
            QueueEntryStatus.ACCEPTED.value,
            owner["user"]["id"],
        ),
    ]


async def test_owner_reject_sets_status_and_event(client: AsyncClient) -> None:
    owner, business, service = await _setup_business_with_service(client)
    customer = await _register(client, CUSTOMER_A)
    opened = await _open_queue(client, owner["access_token"])
    entry = await _join_queue(client, business["id"], customer["access_token"], service["id"])

    rejected = await _reject_entry(client, owner["access_token"], entry["id"])
    snapshot = await _entry_snapshot(entry["id"])
    queue = await _queue_snapshot(opened["id"])

    assert rejected["status"] == "REJECTED"
    assert rejected["token_number"] is None
    assert rejected["position"] is None
    assert snapshot["status"] == QueueEntryStatus.REJECTED
    assert snapshot["token_number"] is None
    assert queue["last_token"] == 0
    assert await _event_snapshot(entry["id"]) == [
        (None, QueueEntryStatus.REQUESTED.value, customer["user"]["id"]),
        (
            QueueEntryStatus.REQUESTED.value,
            QueueEntryStatus.REJECTED.value,
            owner["user"]["id"],
        ),
    ]


async def test_token_allocation_is_sequential(client: AsyncClient) -> None:
    owner, business, service = await _setup_business_with_service(client)
    customer_a = await _register(client, CUSTOMER_A)
    customer_b = await _register(client, CUSTOMER_B)
    opened = await _open_queue(client, owner["access_token"])
    first_entry = await _join_queue(
        client, business["id"], customer_a["access_token"], service["id"]
    )
    second_entry = await _join_queue(
        client, business["id"], customer_b["access_token"], service["id"]
    )

    first = await _accept_entry(client, owner["access_token"], first_entry["id"])
    second = await _accept_entry(client, owner["access_token"], second_entry["id"])
    queue = await _queue_snapshot(opened["id"])

    assert [first["token_number"], second["token_number"]] == [1, 2]
    assert queue["last_token"] == 2


async def test_concurrent_accept_of_one_entry_is_single_winner(
    client: AsyncClient,
) -> None:
    owner, business, service = await _setup_business_with_service(client)
    customer = await _register(client, CUSTOMER_A)
    opened = await _open_queue(client, owner["access_token"])
    entry = await _join_queue(client, business["id"], customer["access_token"], service["id"])

    responses = await asyncio.wait_for(
        asyncio.gather(
            client.post(
                f"{ME_QUEUE_PATH}/entries/{entry['id']}/accept",
                headers=_bearer(owner["access_token"]),
            ),
            client.post(
                f"{ME_QUEUE_PATH}/entries/{entry['id']}/accept",
                headers=_bearer(owner["access_token"]),
            ),
        ),
        timeout=15,
    )

    assert sorted(response.status_code for response in responses) == [200, 409]
    assert (await _entry_snapshot(entry["id"]))["token_number"] == 1
    assert (await _queue_snapshot(opened["id"]))["last_token"] == 1
    events = await _event_snapshot(entry["id"])
    assert len(events) == 2
    assert events[1][1] == QueueEntryStatus.ACCEPTED.value


async def test_accept_and_reject_race_has_one_winner(
    client: AsyncClient,
) -> None:
    owner, business, service = await _setup_business_with_service(client)
    customer = await _register(client, CUSTOMER_A)
    opened = await _open_queue(client, owner["access_token"])
    entry = await _join_queue(
        client, business["id"], customer["access_token"], service["id"]
    )
    headers = _bearer(owner["access_token"])

    responses = await asyncio.wait_for(
        asyncio.gather(
            client.post(
                f"{ME_QUEUE_PATH}/entries/{entry['id']}/accept", headers=headers
            ),
            client.post(
                f"{ME_QUEUE_PATH}/entries/{entry['id']}/reject", headers=headers
            ),
        ),
        timeout=15,
    )

    assert sorted(response.status_code for response in responses) == [200, 409]
    winner = next(response for response in responses if response.status_code == 200)
    snapshot = await _entry_snapshot(entry["id"])
    queue = await _queue_snapshot(opened["id"])
    assert snapshot["status"] == winner.json()["status"]
    assert len(await _event_snapshot(entry["id"])) == 2
    if snapshot["status"] == QueueEntryStatus.ACCEPTED:
        assert snapshot["token_number"] == 1
        assert queue["last_token"] == 1
    else:
        assert snapshot["status"] == QueueEntryStatus.REJECTED
        assert snapshot["token_number"] is None
        assert queue["last_token"] == 0


async def test_concurrent_accepts_allocate_distinct_tokens(
    client: AsyncClient,
) -> None:
    owner, business, service = await _setup_business_with_service(client)
    customer_a = await _register(client, CUSTOMER_A)
    customer_b = await _register(client, CUSTOMER_B)
    opened = await _open_queue(client, owner["access_token"])
    first_entry = await _join_queue(
        client, business["id"], customer_a["access_token"], service["id"]
    )
    second_entry = await _join_queue(
        client, business["id"], customer_b["access_token"], service["id"]
    )

    responses = await asyncio.wait_for(
        asyncio.gather(
            client.post(
                f"{ME_QUEUE_PATH}/entries/{first_entry['id']}/accept",
                headers=_bearer(owner["access_token"]),
            ),
            client.post(
                f"{ME_QUEUE_PATH}/entries/{second_entry['id']}/accept",
                headers=_bearer(owner["access_token"]),
            ),
        ),
        timeout=15,
    )

    assert [response.status_code for response in responses] == [200, 200]
    tokens = sorted(response.json()["token_number"] for response in responses)
    assert tokens == [1, 2]
    assert (await _queue_snapshot(opened["id"]))["last_token"] == 2


async def test_concurrent_open_creates_one_queue(client: AsyncClient) -> None:
    owner, business, _service = await _setup_business_with_service(client)
    headers = _bearer(owner["access_token"])

    responses = await asyncio.wait_for(
        asyncio.gather(
            client.post(ME_QUEUE_PATH, headers=headers),
            client.post(ME_QUEUE_PATH, headers=headers),
        ),
        timeout=15,
    )

    assert [response.status_code for response in responses] == [201, 201]
    assert responses[0].json()["id"] == responses[1].json()["id"]
    async with async_session_factory() as session:
        result = await session.execute(
            select(DailyQueue).where(DailyQueue.business_id == business["id"])
        )
        assert len(result.scalars().all()) == 1


async def test_owner_cannot_accept_or_reject_cross_business_entry(
    client: AsyncClient,
) -> None:
    owner_a, business_a, service_a = await _setup_business_with_service(
        client, owner_payload=OWNER_A, business_name="Queue Salon A"
    )
    owner_b, _business_b, _service_b = await _setup_business_with_service(
        client, owner_payload=OWNER_B, business_name="Queue Salon B"
    )
    customer = await _register(client, CUSTOMER_A)
    await _open_queue(client, owner_a["access_token"])
    entry = await _join_queue(
        client, business_a["id"], customer["access_token"], service_a["id"]
    )

    for action in ("accept", "reject"):
        response = await client.post(
            f"{ME_QUEUE_PATH}/entries/{entry['id']}/{action}",
            headers=_bearer(owner_b["access_token"]),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "queue_entry_not_found"
