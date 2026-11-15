import hashlib
import hmac

import pytest

from src.core import settings

pytestmark = pytest.mark.anyio


def create_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def test_full_order_and_review_lifecycle(client):
    # 1. Admin login setup
    admin_reg = {
        "login": "admin_shop",
        "password": "Password123!",
    }
    from uuid import UUID

    from main import app
    from src.api.dependencies import get_user_uow

    reg_resp = await client.post("/api/v1/auth/register", json=admin_reg)
    admin_id = reg_resp.json()["body"]["user"]["id"]

    get_uow_fn = app.dependency_overrides[get_user_uow]
    uow = get_uow_fn()
    async with uow:
        admin = await uow.users.get_by_id(UUID(admin_id))
        admin.global_permissions = ["*"]
        await uow.users.update(admin)
        await uow.commit()

    admin_login_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin_shop", "password": "Password123!"},
    )
    admin_token = admin_login_resp.json()["body"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Admin creates category, product and variant
    cat_resp = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Clothing", "slug": "clothing"},
    )
    cat_id = cat_resp.json()["body"]["id"]

    prod_resp = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "category_id": cat_id,
            "title": "Winter Jacket",
            "slug": "winter-jacket",
            "base_price": "199.99",
            "is_published": True,
        },
    )
    prod_id = prod_resp.json()["body"]["id"]

    var_resp = await client.post(
        f"/api/v1/products/{prod_id}/variants",
        headers=admin_headers,
        json={
            "sku": "WJ-M-BLK",
            "size": "M",
            "color_name": "Black",
            "stock_quantity": 5,
        },
    )
    variant_id = var_resp.json()["body"]["id"]

    # 3. Buyer registration & address creation
    buyer_reg = {
        "login": "customer_one",
        "password": "Password123!",
    }
    await client.post("/api/v1/auth/register", json=buyer_reg)
    buyer_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "customer_one", "password": "Password123!"},
    )
    buyer_token = buyer_login.json()["body"]["access_token"]
    buyer_headers = {"Authorization": f"Bearer {buyer_token}"}

    addr_resp = await client.post(
        "/api/v1/users/me/addresses",
        headers=buyer_headers,
        json={
            "city": "Hamburg",
            "street": "Jungfernstieg 1",
            "postal_code": "20354",
            "is_default": True,
        },
    )
    address_id = addr_resp.json()["body"]["id"]

    # 4. Buyer adds product to cart
    add_cart_resp = await client.put(
        f"/api/v1/cart/items/{variant_id}",
        headers=buyer_headers,
        json={"quantity": 2},
    )
    assert add_cart_resp.status_code == 200

    # Verify cart
    cart_resp = await client.get("/api/v1/cart", headers=buyer_headers)
    assert cart_resp.status_code == 200
    assert len(cart_resp.json()["body"]["items"]) == 1
    assert cart_resp.json()["body"]["total_amount"] == "399.98"

    # 5. Buyer checkouts
    checkout_resp = await client.post(
        "/api/v1/orders/checkout",
        headers=buyer_headers,
        json={"address_id": address_id, "comment": "Ring twice"},
    )
    assert checkout_resp.status_code == 201
    checkout_data = checkout_resp.json()["body"]
    order_id = checkout_data["order"]["id"]
    assert checkout_data["order"]["status"] == "pending_payment"
    assert checkout_data["order"]["total_amount"] == "399.98"
    assert checkout_data["payment"]["status"] == "pending"

    # Verify cart is empty after checkout
    cart_after = await client.get("/api/v1/cart", headers=buyer_headers)
    assert len(cart_after.json()["body"]["items"]) == 0

    # 6. Payment Webhook
    webhook_payload_dict = {
        "order_id": order_id,
        "external_transaction_id": "stripe_ch_9999",
        "status": "succeeded",
        "paid_amount": 399.98,
    }
    import json

    raw_body = json.dumps(webhook_payload_dict).encode("utf-8")
    signature = create_signature(raw_body, settings.webhook_secret)

    webhook_resp = await client.post(
        "/api/v1/payments/webhook",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
        },
    )
    assert webhook_resp.status_code == 200
    assert webhook_resp.json()["body"]["status"] == "succeeded"

    # 7. Check order is paid
    order_detail = await client.get(f"/api/v1/orders/{order_id}", headers=buyer_headers)
    assert order_detail.json()["body"]["status"] == "paid"

    # 8. Admin updates status to delivered
    status_resp = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        headers=admin_headers,
        json={"status": "processing"},
    )
    assert status_resp.status_code == 200

    status_resp = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        headers=admin_headers,
        json={"status": "shipped"},
    )
    assert status_resp.status_code == 200

    status_resp = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        headers=admin_headers,
        json={"status": "delivered"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["body"]["status"] == "delivered"

    # 9. Buyer posts a review
    review_resp = await client.post(
        f"/api/v1/products/{prod_id}/reviews",
        headers=buyer_headers,
        json={
            "rating": 5,
            "fit_feedback": "true_to_size",
            "comment": "Warm and stylish jacket!",
        },
    )
    assert review_resp.status_code == 201
    review_data = review_resp.json()["body"]
    review_id = review_data["id"]
    assert review_data["rating"] == 5

    # 10. List product reviews (public)
    reviews_list = await client.get(f"/api/v1/products/{prod_id}/reviews")
    assert reviews_list.status_code == 200
    assert len(reviews_list.json()["body"]) == 1

    # 11. Delete review
    del_rev = await client.delete(f"/api/v1/reviews/{review_id}", headers=buyer_headers)
    assert del_rev.status_code == 200
    assert del_rev.json()["body"]["deleted"] is True
