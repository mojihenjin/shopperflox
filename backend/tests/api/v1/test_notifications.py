import hashlib
import hmac
from uuid import UUID

import pytest
from httpx import AsyncClient

from src.core import settings
from src.infrastructure.security import JwtTokenProvider


def create_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.fixture
def auth_headers():
    provider = JwtTokenProvider()

    def _make(user_id: UUID, permissions: list[str] | None = None):
        perms = permissions or []
        token = provider.create_access_token(user_id, perms)
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.mark.anyio
async def test_notifications_crud_and_unread_count(client: AsyncClient, auth_headers):
    # 1. Register a user
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"login": "notif_user", "password": "Password123!"},
    )
    assert reg_resp.status_code == 201
    user_id = UUID(reg_resp.json()["body"]["user"]["id"])
    headers = auth_headers(user_id)

    # 2. Check empty notifications and zero unread count
    list_resp = await client.get("/api/v1/notifications", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["body"] == []
    assert list_resp.json()["metadata"]["total"] == 0

    count_resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert count_resp.status_code == 200
    assert count_resp.json()["body"]["count"] == 0

    # 3. Simulate creating notifications via order flow or notification service
    from src.api.dependencies import get_notification_uow, get_task_queue
    from src.application.services import NotificationService

    uow = client._transport.app.dependency_overrides[get_notification_uow]()  # type: ignore
    tq = client._transport.app.dependency_overrides[get_task_queue]()  # type: ignore
    service = NotificationService(uow=uow, task_queue=tq)

    n1 = await service.notify_user(
        user_id=user_id,
        title="Уведомление 1",
        body="Тело 1",
        link="/test-link-1",
    )
    await service.notify_user(
        user_id=user_id,
        title="Уведомление 2",
        body="Тело 2",
        link="/test-link-2",
    )
    await service.notify_user(
        user_id=user_id,
        title="Уведомление 3",
        body="Тело 3",
        link=None,
    )

    # 4. Check unread count is 3
    count_resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert count_resp.status_code == 200
    assert count_resp.json()["body"]["count"] == 3

    # 5. List with pagination
    list_resp = await client.get(
        "/api/v1/notifications?limit=2&offset=0", headers=headers
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()["body"]) == 2
    assert list_resp.json()["metadata"]["total"] == 3

    # 6. Mark single notification as read
    mark_resp = await client.patch(
        f"/api/v1/notifications/{n1.id}/read", headers=headers
    )
    assert mark_resp.status_code == 200
    assert mark_resp.json()["body"]["id"] == str(n1.id)
    assert mark_resp.json()["body"]["is_read"] is True

    # Check unread count is now 2
    count_resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert count_resp.json()["body"]["count"] == 2

    # 7. Mark all as read
    read_all_resp = await client.post("/api/v1/notifications/read-all", headers=headers)
    assert read_all_resp.status_code == 200
    assert read_all_resp.json()["body"]["marked_count"] == 2

    # Unread count is now 0
    count_resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert count_resp.json()["body"]["count"] == 0


@pytest.mark.anyio
async def test_notifications_isolation(client: AsyncClient, auth_headers):
    # User A
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={"login": "user_alpha", "password": "Password123!"},
    )
    user_a_id = UUID(reg_a.json()["body"]["user"]["id"])
    headers_a = auth_headers(user_a_id)

    # User B
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"login": "user_beta", "password": "Password123!"},
    )
    user_b_id = UUID(reg_b.json()["body"]["user"]["id"])
    headers_b = auth_headers(user_b_id)

    # Create notification for User A
    from src.api.dependencies import get_notification_uow, get_task_queue
    from src.application.services import NotificationService

    uow = client._transport.app.dependency_overrides[get_notification_uow]()  # type: ignore
    tq = client._transport.app.dependency_overrides[get_task_queue]()  # type: ignore
    service = NotificationService(uow=uow, task_queue=tq)

    n = await service.notify_user(
        user_id=user_a_id,
        title="Секрет А",
        body="Только для А",
    )

    # User A lists notifications -> sees 1
    list_a = await client.get("/api/v1/notifications", headers=headers_a)
    assert len(list_a.json()["body"]) == 1

    # User B lists notifications -> empty
    list_b = await client.get("/api/v1/notifications", headers=headers_b)
    assert len(list_b.json()["body"]) == 0

    # User B tries to mark User A's notification as read -> 404
    mark_b = await client.patch(f"/api/v1/notifications/{n.id}/read", headers=headers_b)
    assert mark_b.status_code == 404


@pytest.mark.anyio
async def test_order_shipment_with_post_code_and_notification(
    client: AsyncClient, auth_headers
):
    from src.api.dependencies import get_task_queue

    tq = client._transport.app.dependency_overrides[get_task_queue]()  # type: ignore

    # 1. Admin setup
    admin_reg = await client.post(
        "/api/v1/auth/register",
        json={"login": "admin_ship", "password": "Password123!"},
    )
    admin_id = UUID(admin_reg.json()["body"]["user"]["id"])

    from src.api.dependencies import get_user_uow

    user_uow = client._transport.app.dependency_overrides[get_user_uow]()  # type: ignore
    async with user_uow:
        admin = await user_uow.users.get_by_id(admin_id)
        assert admin is not None
        admin.global_permissions = ["*"]
        await user_uow.users.update(admin)
        await user_uow.commit()

    admin_headers = auth_headers(admin_id, permissions=["*"])

    # 2. Buyer setup with email
    buyer_reg = await client.post(
        "/api/v1/auth/register",
        json={
            "login": "buyer_ship",
            "password": "Password123!",
        },
    )
    buyer_id = UUID(buyer_reg.json()["body"]["user"]["id"])
    buyer_headers = auth_headers(buyer_id)

    # Manually set verified email on buyer in DB to test email dispatch
    async with user_uow:
        buyer = await user_uow.users.get_by_id(buyer_id)
        assert buyer is not None
        buyer.email = "buyer@shopperflox.com"
        buyer.verified_email = True
        await user_uow.users.update(buyer)
        await user_uow.commit()

    # 3. Create category, product, variant
    cat_resp = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Apparel", "slug": "apparel"},
    )
    cat_id = cat_resp.json()["body"]["id"]

    prod_resp = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "category_id": cat_id,
            "title": "Graphic Tee",
            "slug": "graphic-tee",
            "base_price": 50.0,
            "is_published": True,
        },
    )
    prod_id = prod_resp.json()["body"]["id"]

    var_resp = await client.post(
        f"/api/v1/products/{prod_id}/variants",
        headers=admin_headers,
        json={
            "sku": "TEE-BLK-M",
            "size": "M",
            "color_name": "Black",
            "stock_quantity": 10,
        },
    )
    variant_id = var_resp.json()["body"]["id"]

    # 4. Buyer adds to cart and checkouts
    addr_resp = await client.post(
        "/api/v1/users/me/addresses",
        headers=buyer_headers,
        json={
            "city": "Moscow",
            "street": "Tverskaya 1",
            "postal_code": "125009",
            "is_default": True,
        },
    )
    address_id = addr_resp.json()["body"]["id"]

    await client.put(
        f"/api/v1/cart/items/{variant_id}",
        headers=buyer_headers,
        json={"quantity": 2},
    )

    checkout_resp = await client.post(
        "/api/v1/orders/checkout",
        headers=buyer_headers,
        json={"address_id": address_id},
    )
    order_id = checkout_resp.json()["body"]["order"]["id"]

    # Verify product_slug in order items
    items = checkout_resp.json()["body"]["order"]["items"]
    assert len(items) == 1
    assert items[0]["product_slug"] == "graphic-tee"
    assert checkout_resp.json()["body"]["order"]["post_code"] is None

    # 5. Pay order
    import json

    raw_body = json.dumps(
        {
            "order_id": order_id,
            "external_transaction_id": "tx_ship_test",
            "status": "succeeded",
            "paid_amount": 100.0,
        }
    ).encode("utf-8")
    sig = create_signature(raw_body, settings.webhook_secret)
    await client.post(
        "/api/v1/payments/webhook",
        content=raw_body,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": sig},
    )

    # 6. Admin transitions to processing
    await client.patch(
        f"/api/v1/orders/{order_id}/status",
        headers=admin_headers,
        json={"status": "processing"},
    )

    # 7. Admin transitions to shipped with post_code
    ship_resp = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        headers=admin_headers,
        json={"status": "shipped", "post_code": "TRACK-123456789"},
    )
    assert ship_resp.status_code == 200
    assert ship_resp.json()["body"]["status"] == "shipped"
    assert ship_resp.json()["body"]["post_code"] == "TRACK-123456789"

    # 8. Verify buyer received notification
    notif_resp = await client.get("/api/v1/notifications", headers=buyer_headers)
    assert notif_resp.status_code == 200
    notifs = notif_resp.json()["body"]
    assert len(notifs) == 1
    assert notifs[0]["title"] == f"Заказ #{order_id[:8]} передан в доставку"
    assert "TRACK-123456789" in notifs[0]["body"]
    assert "Graphic Tee (x2)" in notifs[0]["body"]
    assert notifs[0]["link"] == "/orders"

    # 9. Verify email was enqueued in task queue
    assert len(tq.sent_emails) == 1
    to_email, subject, body_text = tq.sent_emails[0]
    assert to_email == "buyer@shopperflox.com"
    assert subject == f"Заказ #{order_id[:8]} передан в доставку"
    assert "TRACK-123456789" in body_text

    # 10. Update post_code when already shipped -> triggers update notification and email
    update_ship_resp = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        headers=admin_headers,
        json={"status": "shipped", "post_code": "NEW-TRACK-999"},
    )
    assert update_ship_resp.status_code == 200
    assert update_ship_resp.json()["body"]["post_code"] == "NEW-TRACK-999"

    notif_resp2 = await client.get("/api/v1/notifications", headers=buyer_headers)
    assert len(notif_resp2.json()["body"]) == 2
    assert "NEW-TRACK-999" in notif_resp2.json()["body"][0]["body"]

    assert len(tq.sent_emails) == 2
    assert "NEW-TRACK-999" in tq.sent_emails[1][2]
