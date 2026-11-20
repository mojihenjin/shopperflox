from uuid import UUID

import pytest
from httpx import AsyncClient

from src.api.dependencies import get_user_uow
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


async def create_user_with_perms(
    client: AsyncClient, user_uow, auth_headers, login: str, permissions: list[str]
) -> tuple[UUID, dict[str, str]]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"login": login, "password": "Password123!"},
    )
    user_id = UUID(reg.json()["body"]["user"]["id"])
    async with user_uow:
        u = await user_uow.users.get_by_id(user_id)
        assert u is not None
        u.global_permissions = permissions
        await user_uow.users.update(u)
        await user_uow.commit()
    headers = auth_headers(user_id, permissions=permissions)
    return user_id, headers


async def test_product_and_brand_view_counters(client: AsyncClient, auth_headers):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    creator_id, creator_headers = await create_user_with_perms(
        client,
        user_uow,
        auth_headers,
        login="creator_analytics",
        permissions=["creator:brand", "creator:products", "catalog:manage"],
    )

    mod_id, mod_headers = await create_user_with_perms(
        client,
        user_uow,
        auth_headers,
        login="mod_analytics",
        permissions=["mod:approve_manager", "catalog:manage"],
    )

    cat_res = await client.post(
        "/api/v1/categories",
        headers=mod_headers,
        json={"name": "Dresses", "slug": "dresses"},
    )
    category_id = cat_res.json()["body"]["id"]

    brand_res = await client.post(
        "/api/v1/brands",
        headers=creator_headers,
        json={"name": "Lumiere Atelier"},
    )
    brand_id = brand_res.json()["body"]["id"]

    await client.post(
        f"/api/v1/moderation/brands/{brand_id}/approve",
        headers=mod_headers,
    )

    prod_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "title": "Lumiere Silk Dress",
            "slug": "lumiere-silk-dress",
            "base_price": 8500.0,
            "is_published": True,
        },
    )
    prod_id = prod_res.json()["body"]["id"]

    await client.post(
        f"/api/v1/moderation/products/{prod_id}/approve",
        headers=mod_headers,
    )

    brand_check = await client.get("/api/v1/brands/lumiere-atelier")
    assert brand_check.json()["body"]["views_count"] == 1

    p_check = await client.get("/api/v1/products/lumiere-silk-dress")
    assert p_check.status_code == 200
    assert p_check.json()["body"]["product"]["views_count"] == 1

    brand_check2 = await client.get("/api/v1/brands/lumiere-atelier")
    assert brand_check2.json()["body"]["views_count"] == 3

    p_check2 = await client.get("/api/v1/products/lumiere-silk-dress")
    assert p_check2.json()["body"]["product"]["views_count"] == 2

    brand_check3 = await client.get("/api/v1/brands/lumiere-atelier")
    assert brand_check3.json()["body"]["views_count"] == 5


async def test_orders_counter_increment_on_checkout(client: AsyncClient, auth_headers):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    creator_id, creator_headers = await create_user_with_perms(
        client,
        user_uow,
        auth_headers,
        login="creator_orders",
        permissions=["creator:brand", "creator:products", "catalog:manage"],
    )

    buyer_id, buyer_headers = await create_user_with_perms(
        client,
        user_uow,
        auth_headers,
        login="buyer_orders",
        permissions=[],
    )

    mod_id, mod_headers = await create_user_with_perms(
        client,
        user_uow,
        auth_headers,
        login="mod_orders",
        permissions=["mod:approve_manager"],
    )

    cat_res = await client.post(
        "/api/v1/categories",
        headers=creator_headers,
        json={"name": "Jackets", "slug": "jackets"},
    )
    category_id = cat_res.json()["body"]["id"]

    brand_res = await client.post(
        "/api/v1/brands",
        headers=creator_headers,
        json={"name": "Nordic Warmth"},
    )
    brand_id = brand_res.json()["body"]["id"]
    await client.post(
        f"/api/v1/moderation/brands/{brand_id}/approve",
        headers=mod_headers,
    )

    prod_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "title": "Winter Parka",
            "slug": "winter-parka",
            "base_price": 12000.0,
            "is_published": True,
        },
    )
    prod_id = prod_res.json()["body"]["id"]

    var_res = await client.post(
        f"/api/v1/products/{prod_id}/variants",
        headers=creator_headers,
        json={
            "sku": "WP-BLK-M",
            "size": "M",
            "color_name": "Black",
            "stock_quantity": 20,
        },
    )
    variant_id = var_res.json()["body"]["id"]

    await client.post(
        f"/api/v1/moderation/products/{prod_id}/approve",
        headers=mod_headers,
    )

    addr_res = await client.post(
        "/api/v1/users/me/addresses",
        headers=buyer_headers,
        json={
            "city": "Oslo",
            "street": "Karl Johans gate 1",
            "postal_code": "0154",
            "is_default": True,
        },
    )
    address_id = addr_res.json()["body"]["id"]

    await client.put(
        f"/api/v1/cart/items/{variant_id}",
        headers=buyer_headers,
        json={"quantity": 4},
    )

    checkout_res = await client.post(
        "/api/v1/orders/checkout",
        headers=buyer_headers,
        json={"address_id": address_id},
    )
    assert checkout_res.status_code == 201

    detail_res = await client.get("/api/v1/products/winter-parka")
    assert detail_res.status_code == 200
    prod_body = detail_res.json()["body"]["product"]
    var_body = detail_res.json()["body"]["variants"][0]
    assert prod_body["orders_count"] == 4
    assert var_body["orders_count"] == 4

    brand_body = await client.get("/api/v1/brands/nordic-warmth")
    assert brand_body.json()["body"]["orders_count"] == 4


async def test_brand_moderation_and_verification_endpoints(
    client: AsyncClient, auth_headers
):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    creator_id, creator_headers = await create_user_with_perms(
        client,
        user_uow,
        auth_headers,
        login="mod_brand_creator",
        permissions=["creator:brand"],
    )

    mod_id, mod_headers = await create_user_with_perms(
        client,
        user_uow,
        auth_headers,
        login="mod_brand_admin",
        permissions=["mod:approve_manager"],
    )

    create_res = await client.post(
        "/api/v1/brands",
        headers=creator_headers,
        json={"name": "Aura Studios", "his_url": "https://aura.io"},
    )
    brand_id = create_res.json()["body"]["id"]
    assert create_res.json()["body"]["moderation_status"] == "pending"
    assert create_res.json()["body"]["is_verified"] is False

    count_res = await client.get(
        "/api/v1/moderation/brands/pending-count",
        headers=mod_headers,
    )
    assert count_res.status_code == 200
    assert count_res.json()["body"]["pending_count"] >= 1

    pending_list = await client.get(
        "/api/v1/moderation/brands",
        headers=mod_headers,
    )
    assert pending_list.status_code == 200
    assert any(b["id"] == brand_id for b in pending_list.json()["body"])

    reject_res = await client.post(
        f"/api/v1/moderation/brands/{brand_id}/reject",
        headers=mod_headers,
        json={"reason": "Need official website verification"},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["body"]["moderation_status"] == "rejected"
    assert (
        reject_res.json()["body"]["rejection_reason"]
        == "Need official website verification"
    )

    approve_res = await client.post(
        f"/api/v1/moderation/brands/{brand_id}/approve",
        headers=mod_headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["body"]["moderation_status"] == "approved"
    assert approve_res.json()["body"]["rejection_reason"] is None

    verify_res = await client.patch(
        f"/api/v1/brands/{brand_id}/verify",
        headers=mod_headers,
        json={"is_verified": True},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["body"]["is_verified"] is True

    unverify_res = await client.patch(
        f"/api/v1/brands/{brand_id}/verify",
        headers=mod_headers,
        json={"is_verified": False},
    )
    assert unverify_res.status_code == 200
    assert unverify_res.json()["body"]["is_verified"] is False


async def test_catalog_extended_filters_and_cart_details(
    client: AsyncClient, auth_headers
):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    creator_id, creator_headers = await create_user_with_perms(
        client,
        user_uow,
        auth_headers,
        login="catalog_filter_creator",
        permissions=["creator:brand", "creator:products", "catalog:manage"],
    )

    buyer_id, buyer_headers = await create_user_with_perms(
        client,
        user_uow,
        auth_headers,
        login="filter_buyer",
        permissions=[],
    )

    mod_id, mod_headers = await create_user_with_perms(
        client,
        user_uow,
        auth_headers,
        login="mod_filter",
        permissions=["mod:approve_manager"],
    )

    cat_res = await client.post(
        "/api/v1/categories",
        headers=creator_headers,
        json={"name": "Streetwear", "slug": "streetwear"},
    )
    category_id = cat_res.json()["body"]["id"]

    brand_res = await client.post(
        "/api/v1/brands",
        headers=creator_headers,
        json={"name": "Cyber Street"},
    )
    brand_id = brand_res.json()["body"]["id"]
    await client.post(
        f"/api/v1/moderation/brands/{brand_id}/approve", headers=mod_headers
    )
    await client.patch(
        f"/api/v1/brands/{brand_id}/verify",
        headers=mod_headers,
        json={"is_verified": True},
    )

    p1_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "title": "Neon Cyber Hoodie",
            "slug": "neon-cyber-hoodie",
            "base_price": 6000.0,
            "is_limited": True,
            "is_published": True,
        },
    )
    p1_id = p1_res.json()["body"]["id"]

    p1_var_res = await client.post(
        f"/api/v1/products/{p1_id}/variants",
        headers=creator_headers,
        json={
            "sku": "NCH-PINK-XL",
            "size": "XL",
            "color_name": "Pink",
            "stock_quantity": 5,
        },
    )
    p1_var_id = p1_var_res.json()["body"]["id"]

    await client.post(
        f"/api/v1/products/{p1_id}/images",
        headers=creator_headers,
        json={
            "url": "https://img.cdn/neon-pink.jpg",
            "color": "Pink",
            "sort_order": 1,
            "is_main": True,
        },
    )

    p2_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "title": "Minimalist Black Tee",
            "slug": "minimalist-black-tee",
            "base_price": 2500.0,
            "is_limited": False,
            "is_published": True,
        },
    )
    p2_id = p2_res.json()["body"]["id"]

    await client.post(
        f"/api/v1/products/{p2_id}/variants",
        headers=creator_headers,
        json={
            "sku": "MBT-BLK-S",
            "size": "S",
            "color_name": "Black",
            "stock_quantity": 10,
        },
    )

    await client.post(
        f"/api/v1/moderation/products/{p1_id}/approve", headers=mod_headers
    )
    await client.post(
        f"/api/v1/moderation/products/{p2_id}/approve", headers=mod_headers
    )

    # 1. Test is_limited filter
    lim_res = await client.get("/api/v1/products?is_limited=true")
    assert lim_res.status_code == 200
    lim_ids = [p["id"] for p in lim_res.json()["body"]]
    assert p1_id in lim_ids
    assert p2_id not in lim_ids

    # 2. Test size filter
    size_res = await client.get("/api/v1/products?size=XL")
    assert size_res.status_code == 200
    size_ids = [p["id"] for p in size_res.json()["body"]]
    assert p1_id in size_ids
    assert p2_id not in size_ids

    # 3. Test color filter
    color_res = await client.get("/api/v1/products?color=pink")
    assert color_res.status_code == 200
    color_ids = [p["id"] for p in color_res.json()["body"]]
    assert p1_id in color_ids
    assert p2_id not in color_ids

    # 4. Test images, variants, and brand fields in catalog list
    p1_item = next(p for p in lim_res.json()["body"] if p["id"] == p1_id)
    assert len(p1_item["images"]) == 1
    assert p1_item["images"][0]["url"] == "https://img.cdn/neon-pink.jpg"
    assert len(p1_item["variants"]) == 1
    assert p1_item["variants"][0]["sku"] == "NCH-PINK-XL"
    assert p1_item["brand_id"] == brand_id
    assert p1_item["brand"] == "Cyber Street"
    assert p1_item["brand_is_verified"] is True

    # 5. Test Cart details (product_slug, image_url)
    await client.put(
        f"/api/v1/cart/items/{p1_var_id}",
        headers=buyer_headers,
        json={"quantity": 1},
    )

    cart_res = await client.get("/api/v1/cart", headers=buyer_headers)
    assert cart_res.status_code == 200
    items = cart_res.json()["body"]["items"]
    assert len(items) == 1
    assert items[0]["product_slug"] == "neon-cyber-hoodie"
    assert items[0]["image_url"] == "https://img.cdn/neon-pink.jpg"


async def test_brand_member_permissions_for_variants_and_images(
    client: AsyncClient, auth_headers
):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    creator_id, creator_headers = await create_user_with_perms(
        client,
        user_uow,
        auth_headers,
        login="brand_creator_owner",
        permissions=["creator:brand", "creator:products", "catalog:manage"],
    )

    mod_user_id, mod_user_headers = await create_user_with_perms(
        client,
        user_uow,
        auth_headers,
        login="brand_member_mod",
        permissions=[],
    )

    stranger_id, stranger_headers = await create_user_with_perms(
        client,
        user_uow,
        auth_headers,
        login="stranger_user",
        permissions=[],
    )

    brand_res = await client.post(
        "/api/v1/brands",
        headers=creator_headers,
        json={"name": "Vortex Wear"},
    )
    brand_id = brand_res.json()["body"]["id"]

    # Add User B as brand moderator
    add_m = await client.post(
        f"/api/v1/brands/{brand_id}/members",
        headers=creator_headers,
        json={"login": "brand_member_mod", "role": "moderator"},
    )
    assert add_m.status_code == 201

    cat_res = await client.post(
        "/api/v1/categories",
        headers=creator_headers,
        json={"name": "Pants", "slug": "pants"},
    )
    category_id = cat_res.json()["body"]["id"]

    prod_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": category_id,
            "brand_id": brand_id,
            "title": "Vortex Cargo Pants",
            "slug": "vortex-cargo-pants",
            "base_price": 5000.0,
            "is_published": True,
        },
    )
    prod_id = prod_res.json()["body"]["id"]

    # Brand moderator (User B) adds variant
    var_res = await client.post(
        f"/api/v1/products/{prod_id}/variants",
        headers=mod_user_headers,
        json={
            "sku": "VCP-OLV-32",
            "size": "32",
            "color_name": "Olive",
            "stock_quantity": 5,
        },
    )
    assert var_res.status_code == 201

    # Brand moderator (User B) adds image
    img_res = await client.post(
        f"/api/v1/products/{prod_id}/images",
        headers=mod_user_headers,
        json={"url": "https://img.cdn/vortex-olive.jpg", "color": "Olive"},
    )
    assert img_res.status_code == 201
    img_id = img_res.json()["body"]["id"]

    # Stranger (User C) tries to delete image -> 403
    del_forbidden = await client.delete(
        f"/api/v1/products/{prod_id}/images/{img_id}",
        headers=stranger_headers,
    )
    assert del_forbidden.status_code == 403

    # Brand moderator (User B) deletes image -> 200
    del_ok = await client.delete(
        f"/api/v1/products/{prod_id}/images/{img_id}",
        headers=mod_user_headers,
    )
    assert del_ok.status_code == 200
