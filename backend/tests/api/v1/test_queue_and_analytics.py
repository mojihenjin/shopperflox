from uuid import UUID

import pytest

from main import app
from src.api.dependencies import get_user_uow
from src.domain.models import BrandMemberRole

pytestmark = pytest.mark.anyio


async def _set_permissions(user_id: UUID, perms: list[str]):
    get_uow_fn = app.dependency_overrides[get_user_uow]
    uow = get_uow_fn()
    async with uow:
        user = await uow.users.get_by_id(user_id)
        assert user is not None
        user.global_permissions = perms
        await uow.users.update(user)
        await uow.commit()


async def test_fulfillment_queue_and_sales_analytics(client):
    # 1. Setup Admin
    admin_reg = await client.post(
        "/api/v1/auth/register",
        json={"login": "admin_queue", "password": "Password123!"},
    )
    admin_id = UUID(admin_reg.json()["body"]["user"]["id"])
    await _set_permissions(admin_id, ["*"])

    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin_queue", "password": "Password123!"},
    )
    admin_token = admin_login.json()["body"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create category
    cat_resp = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Queue Category", "slug": "queue-category"},
    )
    cat_id = cat_resp.json()["body"]["id"]

    # 2. Setup Creator for self-worked product
    creator_reg = await client.post(
        "/api/v1/auth/register",
        json={"login": "artisan_creator", "password": "Password123!"},
    )
    creator_id = UUID(creator_reg.json()["body"]["user"]["id"])
    await _set_permissions(creator_id, ["creator:products"])

    creator_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "artisan_creator", "password": "Password123!"},
    )
    creator_token = creator_login.json()["body"]["access_token"]
    creator_headers = {"Authorization": f"Bearer {creator_token}"}

    # Creator creates self-worked product
    prod_resp = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": cat_id,
            "title": "Handmade Leather Bag",
            "slug": "handmade-leather-bag",
            "base_price": "3500.00",
            "price_cny": "270.00",
            "is_self_worked": True,
            "is_published": True,
        },
    )
    assert prod_resp.status_code == 201
    prod_id = prod_resp.json()["body"]["id"]

    # Approve self-worked product
    appr_resp = await client.post(
        f"/api/v1/moderation/products/{prod_id}/approve",
        headers=admin_headers,
    )
    assert appr_resp.status_code == 200

    # Add variant to self-worked product
    var_resp = await client.post(
        f"/api/v1/products/{prod_id}/variants",
        headers=creator_headers,
        json={
            "sku": "HLB-BROWN-01",
            "size": "OneSize",
            "color_name": "Brown",
            "stock_quantity": 10,
        },
    )
    assert var_resp.status_code == 201
    var_id = var_resp.json()["body"]["id"]

    # 3. Setup Customer and make a purchase of self-worked product
    await client.post(
        "/api/v1/auth/register",
        json={"login": "shopper_joe", "password": "Password123!"},
    )
    cust_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "shopper_joe", "password": "Password123!"},
    )
    cust_token = cust_login.json()["body"]["access_token"]
    cust_headers = {"Authorization": f"Bearer {cust_token}"}

    # Update customer personal profile
    await client.patch(
        "/api/v1/users/me/personal",
        headers=cust_headers,
        json={
            "firstname": "Joe",
            "lastname": "Doe",
            "phone_number": "+79991234567",
        },
    )

    # Customer address
    addr_resp = await client.post(
        "/api/v1/users/me/addresses",
        headers=cust_headers,
        json={
            "city": "Moscow",
            "street": "Tverskaya 10",
            "postal_code": "101000",
            "is_default": True,
        },
    )
    addr_id = addr_resp.json()["body"]["id"]

    # Add to cart and checkout
    await client.put(
        f"/api/v1/cart/items/{var_id}",
        headers=cust_headers,
        json={"quantity": 2},
    )
    chk_resp = await client.post(
        "/api/v1/orders/checkout",
        headers=cust_headers,
        json={"address_id": addr_id, "comment": "Handle with care"},
    )
    assert chk_resp.status_code == 201

    # 4. Verify Creator's queue (GET /api/v1/queue/my)
    my_queue_resp = await client.get("/api/v1/queue/my", headers=creator_headers)
    assert my_queue_resp.status_code == 200
    queue_items = my_queue_resp.json()["body"]
    assert len(queue_items) == 1
    item = queue_items[0]

    assert item["product"]["title"] == "Handmade Leather Bag"
    assert item["product"]["slug"] == "handmade-leather-bag"
    assert item["variant"]["sku"] == "HLB-BROWN-01"
    assert item["variant"]["color"] == "Brown"
    assert item["variant"]["size"] == "OneSize"
    assert item["quantity"] == 2
    assert item["unit_price"] == "3500.00"
    assert item["currency"] == "RUB"
    assert item["shipping_address"]["city"] == "Moscow"
    assert item["shipping_address"]["street"] == "Tverskaya 10"
    assert item["shipping_address"]["postal_code"] == "101000"
    assert item["customer"]["login"] == "shopper_joe"
    assert item["customer"]["firstname"] == "Joe"
    assert item["customer"]["lastname"] == "Doe"
    assert item["customer"]["phone_number"] == "+79991234567"
    assert item["fulfillment_status"] == "pending"
    assert item["post_code"] is None
    assert item["tracking_url"] is None

    # Status filter checks
    filter_pending = await client.get(
        "/api/v1/queue/my?status=pending", headers=creator_headers
    )
    assert len(filter_pending.json()["body"]) == 1
    filter_delivered = await client.get(
        "/api/v1/queue/my?status=delivered", headers=creator_headers
    )
    assert len(filter_delivered.json()["body"]) == 0

    item_id = item["id"]

    # 5. Test PATCH /api/v1/queue/items/{item_id}
    # 5a. Unauthorized user tries to update item -> 403
    unauth_patch = await client.patch(
        f"/api/v1/queue/items/{item_id}",
        headers=cust_headers,
        json={"fulfillment_status": "packing"},
    )
    assert unauth_patch.status_code == 403

    # 5b. Creator updates status to packing
    patch1 = await client.patch(
        f"/api/v1/queue/items/{item_id}",
        headers=creator_headers,
        json={"fulfillment_status": "packing"},
    )
    assert patch1.status_code == 200
    assert patch1.json()["body"]["fulfillment_status"] == "packing"

    # 5c. Creator updates post_code (14-digit Russian Post) -> tracking_url auto-resolved
    patch2 = await client.patch(
        f"/api/v1/queue/items/{item_id}",
        headers=creator_headers,
        json={
            "fulfillment_status": "handed_to_post",
            "post_code": "12345678901234",
        },
    )
    assert patch2.status_code == 200
    assert patch2.json()["body"]["fulfillment_status"] == "handed_to_post"
    assert patch2.json()["body"]["post_code"] == "12345678901234"
    assert (
        patch2.json()["body"]["tracking_url"]
        == "https://www.pochta.ru/tracking#12345678901234"
    )

    # 5d. Creator updates post_code (10-digit CDEK) -> tracking_url auto-resolved
    patch3 = await client.patch(
        f"/api/v1/queue/items/{item_id}",
        headers=creator_headers,
        json={"post_code": "1234567890"},
    )
    assert patch3.status_code == 200
    assert (
        patch3.json()["body"]["tracking_url"]
        == "https://www.cdek.ru/ru/tracking?order_id=1234567890"
    )

    # 5e. Creator updates post_code (Boxberry) -> tracking_url auto-resolved
    patch4 = await client.patch(
        f"/api/v1/queue/items/{item_id}",
        headers=creator_headers,
        json={"post_code": "BB12345678"},
    )
    assert patch4.status_code == 200
    assert (
        patch4.json()["body"]["tracking_url"]
        == "https://boxberry.ru/tracking-page?id=BB12345678"
    )

    # 5f. Creator sets manual tracking_url
    patch5 = await client.patch(
        f"/api/v1/queue/items/{item_id}",
        headers=creator_headers,
        json={
            "post_code": "CUSTOM123",
            "tracking_url": "https://custom-courier.com/track/CUSTOM123",
        },
    )
    assert patch5.status_code == 200
    assert (
        patch5.json()["body"]["tracking_url"]
        == "https://custom-courier.com/track/CUSTOM123"
    )

    # 6. Creator Analytics (GET /api/v1/analytics/my)
    creator_analytics = await client.get(
        "/api/v1/analytics/my", headers=creator_headers
    )
    assert creator_analytics.status_code == 200
    c_body = creator_analytics.json()["body"]
    assert c_body["total_units_sold"] == 2
    assert c_body["total_revenue"]["RUB"] == "7000.00"
    assert c_body["total_revenue"]["USD"] == "0.00"
    assert c_body["total_revenue"]["CNY"] == "0.00"
    assert len(c_body["products"]) == 1
    assert c_body["products"][0]["title"] == "Handmade Leather Bag"
    assert c_body["products"][0]["units_sold"] == 2
    assert len(c_body["products"][0]["variants"]) == 1
    assert c_body["products"][0]["variants"][0]["sku"] == "HLB-BROWN-01"
    assert c_body["products"][0]["variants"][0]["units_sold"] == 2

    # 7. Brand Fulfillment Queue & Analytics (with queue_manager role)
    # 7a. Setup Brand and brand product
    brand_rep = await client.post(
        "/api/v1/auth/register",
        json={"login": "brand_boss", "password": "Password123!"},
    )
    rep_id = UUID(brand_rep.json()["body"]["user"]["id"])
    await _set_permissions(rep_id, ["creator:brand"])

    rep_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "brand_boss", "password": "Password123!"},
    )
    rep_token = rep_login.json()["body"]["access_token"]
    rep_headers = {"Authorization": f"Bearer {rep_token}"}

    create_brand_resp = await client.post(
        "/api/v1/brands",
        headers=rep_headers,
        json={"name": "Alpha Atelier"},
    )
    brand_id = create_brand_resp.json()["body"]["id"]

    # Approve brand
    await client.post(
        f"/api/v1/moderation/brands/{brand_id}/approve",
        headers=admin_headers,
    )

    # Add queue_manager to brand
    qm_reg = await client.post(
        "/api/v1/auth/register",
        json={"login": "queue_manager_bob", "password": "Password123!"},
    )
    _ = qm_reg.json()["body"]["user"]["id"]
    qm_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "queue_manager_bob", "password": "Password123!"},
    )
    qm_token = qm_login.json()["body"]["access_token"]
    qm_headers = {"Authorization": f"Bearer {qm_token}"}

    add_member_resp = await client.post(
        f"/api/v1/brands/{brand_id}/members",
        headers=rep_headers,
        json={
            "login": "queue_manager_bob",
            "role": BrandMemberRole.QUEUE_MANAGER.value,
        },
    )
    assert add_member_resp.status_code == 201

    # Create product for brand
    b_prod_resp = await client.post(
        "/api/v1/products",
        headers=rep_headers,
        json={
            "brand_id": brand_id,
            "category_id": cat_id,
            "title": "Alpha Signature Hoodie",
            "slug": "alpha-signature-hoodie",
            "base_price": "5000.00",
            "is_published": True,
        },
    )
    assert b_prod_resp.status_code == 201
    b_prod_id = b_prod_resp.json()["body"]["id"]

    await client.post(
        f"/api/v1/moderation/products/{b_prod_id}/approve",
        headers=admin_headers,
    )

    b_var_resp = await client.post(
        f"/api/v1/products/{b_prod_id}/variants",
        headers=rep_headers,
        json={
            "sku": "ASH-L-BLK",
            "size": "L",
            "color_name": "Black",
            "stock_quantity": 20,
        },
    )
    b_var_id = b_var_resp.json()["body"]["id"]

    # Customer buys brand product
    await client.put(
        f"/api/v1/cart/items/{b_var_id}",
        headers=cust_headers,
        json={"quantity": 1},
    )
    chk_b_resp = await client.post(
        "/api/v1/orders/checkout",
        headers=cust_headers,
        json={"address_id": addr_id},
    )
    assert chk_b_resp.status_code == 201

    # 7b. Queue Manager access to brand queue (GET /api/v1/queue/brands/{brand_id})
    qm_queue = await client.get(f"/api/v1/queue/brands/{brand_id}", headers=qm_headers)
    assert qm_queue.status_code == 200
    b_items = qm_queue.json()["body"]
    assert len(b_items) == 1
    assert b_items[0]["product"]["title"] == "Alpha Signature Hoodie"
    assert b_items[0]["variant"]["sku"] == "ASH-L-BLK"
    assert b_items[0]["unit_price"] == "5000.00"

    # Queue Manager updates status and post_code
    b_item_id = b_items[0]["id"]
    qm_patch = await client.patch(
        f"/api/v1/queue/items/{b_item_id}",
        headers=qm_headers,
        json={"fulfillment_status": "packing", "post_code": "RU123456789RU"},
    )
    assert qm_patch.status_code == 200
    assert qm_patch.json()["body"]["fulfillment_status"] == "packing"
    assert (
        qm_patch.json()["body"]["tracking_url"]
        == "https://www.pochta.ru/tracking#RU123456789RU"
    )

    # Outsider cannot view or patch brand queue
    outsider_queue = await client.get(
        f"/api/v1/queue/brands/{brand_id}", headers=cust_headers
    )
    assert outsider_queue.status_code == 403

    outsider_patch = await client.patch(
        f"/api/v1/queue/items/{b_item_id}",
        headers=cust_headers,
        json={"fulfillment_status": "delivered"},
    )
    assert outsider_patch.status_code == 403

    # 7c. Brand Analytics (GET /api/v1/analytics/brands/{brand_id})
    qm_analytics = await client.get(
        f"/api/v1/analytics/brands/{brand_id}", headers=qm_headers
    )
    assert qm_analytics.status_code == 200
    b_analytics_body = qm_analytics.json()["body"]
    assert b_analytics_body["total_units_sold"] == 1
    assert b_analytics_body["total_revenue"]["RUB"] == "5000.00"
    assert len(b_analytics_body["products"]) == 1
    assert b_analytics_body["products"][0]["title"] == "Alpha Signature Hoodie"

    # Outsider cannot view brand analytics -> 403
    outsider_analytics = await client.get(
        f"/api/v1/analytics/brands/{brand_id}", headers=cust_headers
    )
    assert outsider_analytics.status_code == 403

    # 8. Representative and Moderator roles can also access brand queue & analytics
    # Add moderator
    await client.post(
        "/api/v1/auth/register",
        json={"login": "brand_mod_sam", "password": "Password123!"},
    )
    bm_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "brand_mod_sam", "password": "Password123!"},
    )
    bm_token = bm_login.json()["body"]["access_token"]
    bm_headers = {"Authorization": f"Bearer {bm_token}"}

    await client.post(
        f"/api/v1/brands/{brand_id}/members",
        headers=rep_headers,
        json={"login": "brand_mod_sam", "role": BrandMemberRole.MODERATOR.value},
    )

    bm_queue = await client.get(f"/api/v1/queue/brands/{brand_id}", headers=bm_headers)
    assert bm_queue.status_code == 200
    assert len(bm_queue.json()["body"]) == 1

    bm_analytics = await client.get(
        f"/api/v1/analytics/brands/{brand_id}", headers=bm_headers
    )
    assert bm_analytics.status_code == 200

    # Brand representative access
    rep_queue = await client.get(
        f"/api/v1/queue/brands/{brand_id}", headers=rep_headers
    )
    assert rep_queue.status_code == 200
    assert len(rep_queue.json()["body"]) == 1

    # Admin (*) access
    admin_queue = await client.get(
        f"/api/v1/queue/brands/{brand_id}", headers=admin_headers
    )
    assert admin_queue.status_code == 200

    admin_analytics = await client.get(
        f"/api/v1/analytics/brands/{brand_id}", headers=admin_headers
    )
    assert admin_analytics.status_code == 200

    # 9. Verify UPU tracking resolution and unknown code
    # UPU format
    patch_upu = await client.patch(
        f"/api/v1/queue/items/{b_item_id}",
        headers=rep_headers,
        json={"post_code": "RA123456789RU"},
    )
    assert patch_upu.status_code == 200
    assert (
        patch_upu.json()["body"]["tracking_url"]
        == "https://www.pochta.ru/tracking#RA123456789RU"
    )

    # Unknown code without manual URL -> tracking_url is None
    patch_unknown = await client.patch(
        f"/api/v1/queue/items/{b_item_id}",
        headers=rep_headers,
        json={"post_code": "XYZ123"},
    )
    assert patch_unknown.status_code == 200
    assert patch_unknown.json()["body"]["tracking_url"] is None
