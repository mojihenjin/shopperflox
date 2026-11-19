from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient

from src.api.dependencies import get_user_uow
from src.core import settings
from src.infrastructure.security import JwtTokenProvider

pytestmark = pytest.mark.anyio


@pytest.fixture
def auth_headers():
    provider = JwtTokenProvider()

    def _make(user_id: UUID, permissions: list[str] | None = None):
        perms = permissions or []
        token = provider.create_access_token(user_id, perms)
        return {"Authorization": f"Bearer {token}"}

    return _make


async def _create_test_product(
    client: AsyncClient, admin_headers: dict[str, str]
) -> tuple[str, str]:
    cat_resp = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Test Category", "slug": f"test-cat-{Decimal('1.0')}"},
    )
    cat_id = cat_resp.json()["body"]["id"]

    prod_resp = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "category_id": cat_id,
            "title": "Test Product",
            "slug": f"test-prod-{cat_id[:8]}",
            "base_price": "100.00",
            "is_published": True,
        },
    )
    prod_id = prod_resp.json()["body"]["id"]

    var_resp = await client.post(
        f"/api/v1/products/{prod_id}/variants",
        headers=admin_headers,
        json={
            "sku": f"SKU-{prod_id[:8]}",
            "size": "M",
            "color_name": "Blue",
            "stock_quantity": 20,
        },
    )
    variant_id = var_resp.json()["body"]["id"]
    return prod_id, variant_id


async def test_post_offices_permissions_and_crud(client: AsyncClient, auth_headers):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    # 1. Register users: mail manager, regular user, superadmin
    reg_mgr = await client.post(
        "/api/v1/auth/register",
        json={"login": "mail_mgr", "password": "Password123!"},
    )
    mgr_id = UUID(reg_mgr.json()["body"]["user"]["id"])
    mgr_headers = auth_headers(mgr_id, permissions=["mod:mail-manager"])

    reg_reg = await client.post(
        "/api/v1/auth/register",
        json={"login": "regular_guy", "password": "Password123!"},
    )
    reg_id = UUID(reg_reg.json()["body"]["user"]["id"])
    reg_headers = auth_headers(reg_id)

    async with user_uow:
        m_user = await user_uow.users.get_by_id(mgr_id)
        assert m_user is not None
        m_user.global_permissions = ["mod:mail-manager"]
        await user_uow.users.update(m_user)
        await user_uow.commit()

    # 2. Regular user cannot access admin post offices
    resp_unauth = await client.get("/api/v1/admin/post-offices", headers=reg_headers)
    assert resp_unauth.status_code == 403

    resp_create_unauth = await client.post(
        "/api/v1/admin/post-offices",
        headers=reg_headers,
        json={
            "name": "Point 1",
            "country": "Россия",
            "city": "Москва",
            "house": "10",
            "postal_code": "101000",
        },
    )
    assert resp_create_unauth.status_code == 403

    # 3. Mail manager creates post office 1 (active)
    resp_p1 = await client.post(
        "/api/v1/admin/post-offices",
        headers=mgr_headers,
        json={
            "name": "Почта России №620000",
            "country": "Россия",
            "region": "Свердловская область",
            "city": "Екатеринбург",
            "house": "Главпочтамт 1",
            "postal_code": "620000",
            "note": "Центральное отделение",
            "is_active": True,
        },
    )
    assert resp_p1.status_code == 201
    p1_data = resp_p1.json()["body"]
    p1_id = p1_data["id"]
    assert p1_data["name"] == "Почта России №620000"
    assert p1_data["city"] == "Екатеринбург"
    assert p1_data["is_active"] is True

    # Mail manager creates post office 2 (inactive)
    resp_p2 = await client.post(
        "/api/v1/admin/post-offices",
        headers=mgr_headers,
        json={
            "name": "Почта России №620014",
            "country": "Россия",
            "region": "Свердловская область",
            "city": "Екатеринбург",
            "house": "14",
            "postal_code": "620014",
            "is_active": False,
        },
    )
    assert resp_p2.status_code == 201
    p2_id = resp_p2.json()["body"]["id"]

    # 4. Admin list sees both
    resp_admin_list = await client.get(
        "/api/v1/admin/post-offices", headers=mgr_headers
    )
    assert resp_admin_list.status_code == 200
    all_admin = resp_admin_list.json()["body"]
    ids_admin = [o["id"] for o in all_admin]
    assert p1_id in ids_admin
    assert p2_id in ids_admin

    # Search filter in admin list
    resp_search = await client.get(
        "/api/v1/admin/post-offices?search=620000", headers=mgr_headers
    )
    assert resp_search.status_code == 200
    search_ids = [o["id"] for o in resp_search.json()["body"]]
    assert p1_id in search_ids
    assert p2_id not in search_ids

    # 5. Public list only sees active post offices
    resp_public_list = await client.get("/api/v1/post-offices")
    assert resp_public_list.status_code == 200
    all_public = resp_public_list.json()["body"]
    ids_public = [o["id"] for o in all_public]
    assert p1_id in ids_public
    assert p2_id not in ids_public

    # 6. Mail manager updates post office 2 -> set active = True
    resp_patch = await client.patch(
        f"/api/v1/admin/post-offices/{p2_id}",
        headers=mgr_headers,
        json={"is_active": True, "note": "Отделение открылось"},
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["body"]["is_active"] is True
    assert resp_patch.json()["body"]["note"] == "Отделение открылось"

    # Now p2 appears in public list
    resp_pub_after = await client.get("/api/v1/post-offices")
    ids_pub_after = [o["id"] for o in resp_pub_after.json()["body"]]
    assert p2_id in ids_pub_after

    # 7. Delete post office
    resp_del = await client.delete(
        f"/api/v1/admin/post-offices/{p2_id}", headers=mgr_headers
    )
    assert resp_del.status_code == 200
    assert resp_del.json()["body"]["deleted"] is True

    # Verify p2 no longer in list
    resp_pub_final = await client.get("/api/v1/post-offices")
    ids_pub_final = [o["id"] for o in resp_pub_final.json()["body"]]
    assert p2_id not in ids_pub_final


async def test_checkout_structured_address_and_profile_saving(
    client: AsyncClient, auth_headers
):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    # 1. Setup admin and buyer
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "admin_checkout", "password": "Password123!"},
    )
    admin_id = UUID(reg_admin.json()["body"]["user"]["id"])
    admin_headers = auth_headers(admin_id, permissions=["*"])

    async with user_uow:
        a_user = await user_uow.users.get_by_id(admin_id)
        assert a_user is not None
        a_user.global_permissions = ["*"]
        await user_uow.users.update(a_user)
        await user_uow.commit()

    _, variant_id = await _create_test_product(client, admin_headers)

    reg_buyer = await client.post(
        "/api/v1/auth/register",
        json={"login": "buyer_structured", "password": "Password123!"},
    )
    buyer_id = UUID(reg_buyer.json()["body"]["user"]["id"])
    buyer_headers = auth_headers(buyer_id)

    # 2. Add to cart
    await client.put(
        f"/api/v1/cart/items/{variant_id}",
        headers=buyer_headers,
        json={"quantity": 2},
    )

    # 3. Checkout with address and save_to_profile = True
    checkout_payload = {
        "recipient_firstname": "Алексей",
        "recipient_lastname": "Смирнов",
        "recipient_middlename": "Владимирович",
        "save_to_profile": True,
        "passport_series": "4510",
        "passport_number": "123456",
        "delivery_type": "address",
        "country": "Россия",
        "region": "Московская область",
        "city": "Москва",
        "house": "12",
        "apartment": "34",
        "postal_code": "125009",
        "save_address_to_profile": True,
        "comment": "Позвонить перед доставкой",
    }
    resp_checkout = await client.post(
        "/api/v1/orders/checkout",
        headers=buyer_headers,
        json=checkout_payload,
    )
    assert resp_checkout.status_code == 201
    body = resp_checkout.json()["body"]
    order = body["order"]
    assert order["recipient_firstname"] == "Алексей"
    assert order["recipient_lastname"] == "Смирнов"
    assert order["recipient_middlename"] == "Владимирович"
    assert order["passport_series"] == "4510"
    assert order["passport_number"] == "123456"
    assert order["shipping_city"] == "Москва"
    assert order["shipping_house"] == "12"
    assert order["shipping_apartment"] == "34"
    assert order["shipping_postal_code"] == "125009"
    assert order["status"] == "awaiting_payment"

    # 4. Check user profile: personal info is saved, but passport is NEVER in profile
    resp_me = await client.get("/api/v1/users/me", headers=buyer_headers)
    assert resp_me.status_code == 200
    personal_data = resp_me.json()["body"]["personal"]
    assert personal_data is not None
    assert personal_data["firstname"] == "Алексей"
    assert personal_data["lastname"] == "Смирнов"
    assert personal_data["middlename"] == "Владимирович"
    assert "passport_series" not in personal_data
    assert "passport_number" not in personal_data

    # Check user address is saved
    resp_me_addr = await client.get("/api/v1/users/me/addresses", headers=buyer_headers)
    assert resp_me_addr.status_code == 200
    addresses = resp_me_addr.json()["body"]
    assert len(addresses) >= 1
    found = any(
        a["city"] == "Москва" and a["house"] == "12" and a["apartment"] == "34"
        for a in addresses
    )
    assert found


async def test_checkout_post_office_delivery(client: AsyncClient, auth_headers):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "admin_post", "password": "Password123!"},
    )
    admin_id = UUID(reg_admin.json()["body"]["user"]["id"])
    admin_headers = auth_headers(admin_id, permissions=["*"])

    async with user_uow:
        a_user = await user_uow.users.get_by_id(admin_id)
        assert a_user is not None
        a_user.global_permissions = ["*"]
        await user_uow.users.update(a_user)
        await user_uow.commit()

    _, variant_id = await _create_test_product(client, admin_headers)

    # Create post office
    resp_po = await client.post(
        "/api/v1/admin/post-offices",
        headers=admin_headers,
        json={
            "name": "Отделение связи Казань 420000",
            "country": "Россия",
            "region": "Татарстан",
            "city": "Казань",
            "house": "Кремлевская 8",
            "postal_code": "420000",
            "is_active": True,
        },
    )
    assert resp_po.status_code == 201
    po_id = resp_po.json()["body"]["id"]

    reg_buyer = await client.post(
        "/api/v1/auth/register",
        json={"login": "buyer_post", "password": "Password123!"},
    )
    buyer_id = UUID(reg_buyer.json()["body"]["user"]["id"])
    buyer_headers = auth_headers(buyer_id)

    await client.put(
        f"/api/v1/cart/items/{variant_id}",
        headers=buyer_headers,
        json={"quantity": 1},
    )

    checkout_payload = {
        "recipient_firstname": "Гульназ",
        "recipient_lastname": "Хабибуллина",
        "passport_series": "9215",
        "passport_number": "654321",
        "delivery_type": "post_office",
        "post_office_id": po_id,
    }
    resp_checkout = await client.post(
        "/api/v1/orders/checkout",
        headers=buyer_headers,
        json=checkout_payload,
    )
    assert resp_checkout.status_code == 201
    order = resp_checkout.json()["body"]["order"]
    assert order["delivery_type"] == "post_office"
    assert order["post_office_id"] == po_id
    assert order["shipping_city"] == "Казань"
    assert order["shipping_postal_code"] == "420000"
    assert order["shipping_house"] == "Кремлевская 8"


async def test_passport_lifecycle_and_deletion(client: AsyncClient, auth_headers):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "admin_pass", "password": "Password123!"},
    )
    admin_id = UUID(reg_admin.json()["body"]["user"]["id"])
    admin_headers = auth_headers(admin_id, permissions=["*"])

    async with user_uow:
        a_user = await user_uow.users.get_by_id(admin_id)
        assert a_user is not None
        a_user.global_permissions = ["*"]
        await user_uow.users.update(a_user)
        await user_uow.commit()

    _, variant_id = await _create_test_product(client, admin_headers)

    reg_buyer = await client.post(
        "/api/v1/auth/register",
        json={"login": "buyer_pass", "password": "Password123!"},
    )
    buyer_id = UUID(reg_buyer.json()["body"]["user"]["id"])
    buyer_headers = auth_headers(buyer_id)

    await client.put(
        f"/api/v1/cart/items/{variant_id}",
        headers=buyer_headers,
        json={"quantity": 1},
    )

    checkout_payload = {
        "recipient_firstname": "Петр",
        "recipient_lastname": "Петров",
        "passport_series": "2200",
        "passport_number": "778899",
        "delivery_type": "address",
        "city": "Самара",
        "house": "5",
        "postal_code": "443000",
    }
    resp_checkout = await client.post(
        "/api/v1/orders/checkout",
        headers=buyer_headers,
        json=checkout_payload,
    )
    assert resp_checkout.status_code == 201
    order_id = resp_checkout.json()["body"]["order"]["id"]

    # 1. Try to delete passport while order is awaiting_payment -> 400 Bad Request
    resp_del_early = await client.delete(
        f"/api/v1/orders/{order_id}/passport",
        headers=buyer_headers,
    )
    assert resp_del_early.status_code == 400
    assert (
        "Паспортные данные можно удалить только после получения или возврата заказа"
        in resp_del_early.text
    )

    # 2. Advance order status through admin: awaiting_payment -> pending -> packing -> handed_to_post -> in_transit
    statuses_to_test = [
        "pending",
        "packing",
        "handed_to_post",
        "in_transit",
        "returning",
    ]
    for st in statuses_to_test:
        patch_resp = await client.patch(
            f"/api/v1/orders/{order_id}/status",
            headers=admin_headers,
            json={"status": st},
        )
        assert patch_resp.status_code == 200
        # Deleting passport should still fail
        resp_fail = await client.delete(
            f"/api/v1/orders/{order_id}/passport",
            headers=buyer_headers,
        )
        assert resp_fail.status_code == 400

    # 3. Advance to 'returned' -> passport is auto-cleared upon transition!
    patch_returned = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        headers=admin_headers,
        json={"status": "returned"},
    )
    assert patch_returned.status_code == 200
    order_after_returned = patch_returned.json()["body"]
    assert order_after_returned["status"] == "returned"
    assert order_after_returned["passport_series"] is None
    assert order_after_returned["passport_number"] is None

    # Deleting passport now returns 200 OK
    resp_del_ok = await client.delete(
        f"/api/v1/orders/{order_id}/passport",
        headers=buyer_headers,
    )
    assert resp_del_ok.status_code == 200
    assert resp_del_ok.json()["body"]["deleted"] is True


async def test_payment_modes_and_debug_pay(
    client: AsyncClient, auth_headers, monkeypatch
):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "admin_modes", "password": "Password123!"},
    )
    admin_id = UUID(reg_admin.json()["body"]["user"]["id"])
    admin_headers = auth_headers(admin_id, permissions=["*"])

    async with user_uow:
        a_user = await user_uow.users.get_by_id(admin_id)
        assert a_user is not None
        a_user.global_permissions = ["*"]
        await user_uow.users.update(a_user)
        await user_uow.commit()

    _, variant_id = await _create_test_product(client, admin_headers)

    reg_buyer = await client.post(
        "/api/v1/auth/register",
        json={"login": "buyer_modes", "password": "Password123!"},
    )
    buyer_id = UUID(reg_buyer.json()["body"]["user"]["id"])
    buyer_headers = auth_headers(buyer_id)

    base_checkout_payload = {
        "recipient_firstname": "Тест",
        "recipient_lastname": "Тестов",
        "passport_series": "1111",
        "passport_number": "222222",
        "delivery_type": "address",
        "city": "Тверь",
        "house": "1",
        "postal_code": "170000",
    }

    # --- Mode 1: Billing enabled ---
    monkeypatch.setattr(settings, "billing_enabled", True)
    monkeypatch.setattr(settings, "billing_url", "https://billing.example.com/pay")
    monkeypatch.setattr(settings, "debug", False)

    await client.put(
        f"/api/v1/cart/items/{variant_id}", headers=buyer_headers, json={"quantity": 1}
    )
    resp1 = await client.post(
        "/api/v1/orders/checkout", headers=buyer_headers, json=base_checkout_payload
    )
    assert resp1.status_code == 201
    body1 = resp1.json()["body"]
    assert body1["payment_mode"] == "billing"
    assert body1["payment_url"] is not None
    assert "https://billing.example.com/pay?order_id=" in body1["payment_url"]
    order_id_1 = body1["order"]["id"]

    # debug-pay must fail with 403 because billing_enabled is True
    resp_dbg_fail1 = await client.post(
        f"/api/v1/orders/{order_id_1}/debug-pay", headers=buyer_headers
    )
    assert resp_dbg_fail1.status_code == 403

    # --- Mode 2: Debug mode ---
    monkeypatch.setattr(settings, "billing_enabled", False)
    monkeypatch.setattr(settings, "billing_url", "")
    monkeypatch.setattr(settings, "debug", True)

    await client.put(
        f"/api/v1/cart/items/{variant_id}", headers=buyer_headers, json={"quantity": 1}
    )
    resp2 = await client.post(
        "/api/v1/orders/checkout", headers=buyer_headers, json=base_checkout_payload
    )
    assert resp2.status_code == 201
    body2 = resp2.json()["body"]
    assert body2["payment_mode"] == "debug"
    assert body2["payment_url"] is None
    order_id_2 = body2["order"]["id"]

    # debug-pay should succeed!
    resp_dbg_ok = await client.post(
        f"/api/v1/orders/{order_id_2}/debug-pay", headers=buyer_headers
    )
    assert resp_dbg_ok.status_code == 200
    paid_order = resp_dbg_ok.json()["body"]
    assert paid_order["is_paid"] is True
    assert paid_order["paid_at"] is not None
    assert paid_order["status"] == "pending"

    # --- Mode 3: Unavailable mode ---
    monkeypatch.setattr(settings, "billing_enabled", False)
    monkeypatch.setattr(settings, "billing_url", "")
    monkeypatch.setattr(settings, "debug", False)

    await client.put(
        f"/api/v1/cart/items/{variant_id}", headers=buyer_headers, json={"quantity": 1}
    )
    resp3 = await client.post(
        "/api/v1/orders/checkout", headers=buyer_headers, json=base_checkout_payload
    )
    assert resp3.status_code == 201
    body3 = resp3.json()["body"]
    assert body3["payment_mode"] == "unavailable"
    assert body3["payment_url"] is None
    order_id_3 = body3["order"]["id"]

    # debug-pay must fail with 403 because debug is False
    resp_dbg_fail3 = await client.post(
        f"/api/v1/orders/{order_id_3}/debug-pay", headers=buyer_headers
    )
    assert resp_dbg_fail3.status_code == 403


async def test_queue_returning_and_returned_lifecycle(
    client: AsyncClient, auth_headers, monkeypatch
):
    monkeypatch.setattr(settings, "debug", True)
    monkeypatch.setattr(settings, "billing_enabled", False)
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    # 1. Admin setup
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "admin_queue", "password": "Password123!"},
    )
    admin_id = UUID(reg_admin.json()["body"]["user"]["id"])
    admin_headers = auth_headers(admin_id, permissions=["*"])

    async with user_uow:
        a_user = await user_uow.users.get_by_id(admin_id)
        assert a_user is not None
        a_user.global_permissions = ["*"]
        await user_uow.users.update(a_user)
        await user_uow.commit()

    _, variant_id = await _create_test_product(client, admin_headers)

    # 2. Buyer setup
    reg_buyer = await client.post(
        "/api/v1/auth/register",
        json={"login": "buyer_queue", "password": "Password123!"},
    )
    buyer_id = UUID(reg_buyer.json()["body"]["user"]["id"])
    buyer_headers = auth_headers(buyer_id)

    await client.put(
        f"/api/v1/cart/items/{variant_id}", headers=buyer_headers, json={"quantity": 1}
    )
    resp_order = await client.post(
        "/api/v1/orders/checkout",
        headers=buyer_headers,
        json={
            "recipient_firstname": "Сергей",
            "recipient_lastname": "Сергеев",
            "passport_series": "3344",
            "passport_number": "556677",
            "delivery_type": "address",
            "city": "Сочи",
            "house": "22",
            "postal_code": "354000",
        },
    )
    assert resp_order.status_code == 201
    order_id = resp_order.json()["body"]["order"]["id"]

    # Use debug-pay to advance to PENDING
    resp_pay = await client.post(
        f"/api/v1/orders/{order_id}/debug-pay", headers=buyer_headers
    )
    assert resp_pay.status_code == 200

    # Get order detail to retrieve item_id
    detail_resp = await client.get(f"/api/v1/orders/{order_id}", headers=buyer_headers)
    assert detail_resp.status_code == 200
    items = detail_resp.json()["body"]["items"]
    assert len(items) == 1
    item_id = items[0]["id"]

    # 3. Queue manager / admin updates item: pending -> packing -> handed_to_post -> in_transit -> returning
    for next_st in ["packing", "handed_to_post", "in_transit", "returning"]:
        q_patch = await client.patch(
            f"/api/v1/queue/items/{item_id}",
            headers=admin_headers,
            json={"fulfillment_status": next_st},
        )
        assert q_patch.status_code == 200
        assert q_patch.json()["body"]["fulfillment_status"] == next_st

    # Check order status is now 'returning'
    ord_ret = await client.get(f"/api/v1/orders/{order_id}", headers=buyer_headers)
    assert ord_ret.json()["body"]["status"] == "returning"
    # Passport is still retained in returning
    assert ord_ret.json()["body"]["passport_series"] == "3344"

    # 4. Advance item to 'returned'
    q_returned = await client.patch(
        f"/api/v1/queue/items/{item_id}",
        headers=admin_headers,
        json={"fulfillment_status": "returned"},
    )
    assert q_returned.status_code == 200
    assert q_returned.json()["body"]["fulfillment_status"] == "returned"

    # Check order status is now 'returned' and passport is auto-cleared to None!
    ord_final = await client.get(f"/api/v1/orders/{order_id}", headers=buyer_headers)
    assert ord_final.json()["body"]["status"] == "returned"
    assert ord_final.json()["body"]["passport_series"] is None
    assert ord_final.json()["body"]["passport_number"] is None
