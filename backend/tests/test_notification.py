from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.db.session import async_session_factory
from app.models.enums import NotificationType
from app.models.notification import Notification

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_PATH = "/api/v1/auth/register"
NOTIFICATIONS_PATH = "/api/v1/notifications"

CUSTOMER_A = {
    "email": "inbox-customer-a@example.com",
    "password": "password123",
    "full_name": "Inbox Customer A",
    "role": "CUSTOMER",
}
CUSTOMER_B = {
    "email": "inbox-customer-b@example.com",
    "password": "password123",
    "full_name": "Inbox Customer B",
    "role": "CUSTOMER",
}

BASE_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, payload: dict) -> dict:
    response = await client.post(REGISTER_PATH, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _seed_notifications(
    user_id: int,
    count: int,
    *,
    notification_type: NotificationType = NotificationType.QUEUE_ACCEPTED,
    is_read: bool = False,
) -> list[int]:
    """Create `count` notifications for a user, oldest first."""
    ids: list[int] = []
    async with async_session_factory() as session:
        for index in range(count):
            notification = Notification(
                user_id=user_id,
                title=f"Title {index}",
                body=f"Body {index}",
                type=notification_type,
                queue_entry_id=None,
                is_read=is_read,
                created_at=BASE_TIME + timedelta(minutes=index),
            )
            session.add(notification)
            await session.flush()
            ids.append(notification.id)
        await session.commit()
    return ids


async def _list_notifications(
    client: AsyncClient, token: str, **params: int
) -> dict:
    response = await client.get(
        NOTIFICATIONS_PATH, params=params, headers=_bearer(token)
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_notification_list_is_scoped_to_current_user(
    client: AsyncClient,
) -> None:
    customer_a = await _register(client, CUSTOMER_A)
    customer_b = await _register(client, CUSTOMER_B)
    mine = await _seed_notifications(customer_a["user"]["id"], 2)
    await _seed_notifications(customer_b["user"]["id"], 3)

    body = await _list_notifications(client, customer_a["access_token"])

    assert [item["id"] for item in body["items"]] == list(reversed(mine))
    assert body["unread_count"] == 2
    assert body["has_more"] is False


async def test_notification_item_exposes_only_minimal_fields(
    client: AsyncClient,
) -> None:
    customer = await _register(client, CUSTOMER_A)
    seeded = await _seed_notifications(customer["user"]["id"], 1)

    body = await _list_notifications(client, customer["access_token"])

    assert set(body["items"][0]) == {
        "id",
        "type",
        "title",
        "body",
        "queue_entry_id",
        "is_read",
        "created_at",
    }
    assert set(body) == {"items", "unread_count", "has_more"}
    assert body["items"][0]["id"] == seeded[0]
    assert body["items"][0]["type"] == NotificationType.QUEUE_ACCEPTED.value
    assert body["items"][0]["queue_entry_id"] is None
    assert body["items"][0]["is_read"] is False


async def test_notification_list_is_newest_first(client: AsyncClient) -> None:
    customer = await _register(client, CUSTOMER_A)
    seeded = await _seed_notifications(customer["user"]["id"], 3)

    body = await _list_notifications(client, customer["access_token"])

    assert [item["id"] for item in body["items"]] == list(reversed(seeded))
    assert body["items"][0]["title"] == "Title 2"


async def test_notification_list_paginates(client: AsyncClient) -> None:
    customer = await _register(client, CUSTOMER_A)
    seeded = await _seed_notifications(customer["user"]["id"], 3)

    first = await _list_notifications(
        client, customer["access_token"], limit=2, offset=0
    )
    second = await _list_notifications(
        client, customer["access_token"], limit=2, offset=2
    )

    assert [item["id"] for item in first["items"]] == [
        seeded[2],
        seeded[1],
    ]
    assert first["has_more"] is True
    assert [item["id"] for item in second["items"]] == [seeded[0]]
    assert second["has_more"] is False


async def test_notification_list_validates_pagination(
    client: AsyncClient,
) -> None:
    customer = await _register(client, CUSTOMER_A)
    headers = _bearer(customer["access_token"])

    too_small = await client.get(
        NOTIFICATIONS_PATH, params={"limit": 0}, headers=headers
    )
    too_large = await client.get(
        NOTIFICATIONS_PATH, params={"limit": 101}, headers=headers
    )
    negative_offset = await client.get(
        NOTIFICATIONS_PATH, params={"offset": -1}, headers=headers
    )

    assert too_small.status_code == 422, too_small.text
    assert too_large.status_code == 422, too_large.text
    assert negative_offset.status_code == 422, negative_offset.text


async def test_notification_list_reports_unread_count(
    client: AsyncClient,
) -> None:
    customer = await _register(client, CUSTOMER_A)
    seeded = await _seed_notifications(customer["user"]["id"], 3)
    response = await client.post(
        f"{NOTIFICATIONS_PATH}/{seeded[0]}/read",
        headers=_bearer(customer["access_token"]),
    )
    assert response.status_code == 200, response.text

    body = await _list_notifications(client, customer["access_token"])

    assert body["unread_count"] == 2


async def test_mark_notification_as_read(client: AsyncClient) -> None:
    customer = await _register(client, CUSTOMER_A)
    seeded = await _seed_notifications(customer["user"]["id"], 1)

    response = await client.post(
        f"{NOTIFICATIONS_PATH}/{seeded[0]}/read",
        headers=_bearer(customer["access_token"]),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == seeded[0]
    assert body["is_read"] is True

    listing = await _list_notifications(client, customer["access_token"])
    assert listing["items"][0]["is_read"] is True
    assert listing["unread_count"] == 0


async def test_mark_notification_as_read_is_idempotent(
    client: AsyncClient,
) -> None:
    customer = await _register(client, CUSTOMER_A)
    seeded = await _seed_notifications(customer["user"]["id"], 1)
    path = f"{NOTIFICATIONS_PATH}/{seeded[0]}/read"
    headers = _bearer(customer["access_token"])

    first = await client.post(path, headers=headers)
    second = await client.post(path, headers=headers)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json() == second.json()

    listing = await _list_notifications(client, customer["access_token"])
    assert listing["items"][0]["is_read"] is True
    assert listing["unread_count"] == 0


async def test_cannot_mark_another_users_notification_read(
    client: AsyncClient,
) -> None:
    customer_a = await _register(client, CUSTOMER_A)
    customer_b = await _register(client, CUSTOMER_B)
    seeded = await _seed_notifications(customer_a["user"]["id"], 1)

    response = await client.post(
        f"{NOTIFICATIONS_PATH}/{seeded[0]}/read",
        headers=_bearer(customer_b["access_token"]),
    )

    assert response.status_code == 403, response.text
    assert response.json()["code"] == "not_notification_owner"

    owner_listing = await _list_notifications(client, customer_a["access_token"])
    assert owner_listing["items"][0]["is_read"] is False
    assert owner_listing["unread_count"] == 1


async def test_mark_missing_notification_returns_not_found(
    client: AsyncClient,
) -> None:
    customer = await _register(client, CUSTOMER_A)

    response = await client.post(
        f"{NOTIFICATIONS_PATH}/999999/read",
        headers=_bearer(customer["access_token"]),
    )

    assert response.status_code == 404, response.text
    assert response.json()["code"] == "notification_not_found"


async def test_notification_endpoints_require_authentication(
    client: AsyncClient,
) -> None:
    listing = await client.get(NOTIFICATIONS_PATH)
    marking = await client.post(f"{NOTIFICATIONS_PATH}/1/read")

    assert listing.status_code == 401, listing.text
    assert listing.json()["code"] == "missing_token"
    assert marking.status_code == 401, marking.text
    assert marking.json()["code"] == "missing_token"
