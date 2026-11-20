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


async def test_brand_creation_and_permission_boundaries(
    client: AsyncClient, auth_headers
):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    # 1. Register users
    reg_creator = await client.post(
        "/api/v1/auth/register",
        json={"login": "brand_creator_1", "password": "Password123!"},
    )
    creator_id = UUID(reg_creator.json()["body"]["user"]["id"])
    creator_headers = auth_headers(creator_id, permissions=["creator:brand"])

    reg_regular = await client.post(
        "/api/v1/auth/register",
        json={"login": "regular_user_1", "password": "Password123!"},
    )
    regular_id = UUID(reg_regular.json()["body"]["user"]["id"])
    regular_headers = auth_headers(regular_id)

    async with user_uow:
        c_user = await user_uow.users.get_by_id(creator_id)
        assert c_user is not None
        c_user.global_permissions = ["creator:brand"]
        await user_uow.users.update(c_user)
        await user_uow.commit()

    # Regular user cannot create a brand
    forbidden_res = await client.post(
        "/api/v1/brands",
        headers=regular_headers,
        json={"name": "Forbidden Brand"},
    )
    assert forbidden_res.status_code == 403

    # Creator creates a brand
    create_res = await client.post(
        "/api/v1/brands",
        headers=creator_headers,
        json={"name": "Synapse Clothing", "his_url": "https://synapse.io"},
    )
    assert create_res.status_code == 201
    brand_data = create_res.json()["body"]
    brand_id = brand_data["id"]
    assert brand_data["name"] == "Synapse Clothing"
    assert brand_data["slug"] == "synapse-clothing"
    assert brand_data["his_url"] == "https://synapse.io"
    assert brand_data["is_deleted"] is False

    # Creator is listed in brand members with role representative
    members_res = await client.get(
        f"/api/v1/brands/{brand_id}/members",
        headers=creator_headers,
    )
    assert members_res.status_code == 200
    members = members_res.json()["body"]
    assert len(members) == 1
    assert members[0]["user_id"] == str(creator_id)
    assert members[0]["user_login"] == "brand_creator_1"
    assert members[0]["role"] == "representative"

    # GET /api/v1/brands/my returns this brand
    my_res = await client.get("/api/v1/brands/my", headers=creator_headers)
    assert my_res.status_code == 200
    my_brands = my_res.json()["body"]
    assert len(my_brands) == 1
    assert my_brands[0]["brand"]["id"] == brand_id
    assert my_brands[0]["role"] == "representative"

    # Before approval, brand is not in active brands
    list_res_before = await client.get("/api/v1/brands")
    assert not any(b["id"] == brand_id for b in list_res_before.json()["body"])

    # Unauthenticated GET /api/v1/brands/{slug} returns 404 for pending brand
    get_res_unauth = await client.get("/api/v1/brands/synapse-clothing")
    assert get_res_unauth.status_code == 404

    # Member can see pending brand by slug
    get_res_member = await client.get(
        "/api/v1/brands/synapse-clothing", headers=creator_headers
    )
    assert get_res_member.status_code == 200

    # Moderator approves brand
    reg_mod = await client.post(
        "/api/v1/auth/register",
        json={"login": "brand_mod_approver", "password": "Password123!"},
    )
    mod_id = UUID(reg_mod.json()["body"]["user"]["id"])
    async with user_uow:
        m_user = await user_uow.users.get_by_id(mod_id)
        assert m_user is not None
        m_user.global_permissions = ["mod:approve_manager"]
        await user_uow.users.update(m_user)
        await user_uow.commit()

    mod_headers = auth_headers(mod_id, permissions=["mod:approve_manager"])
    appr_res = await client.post(
        f"/api/v1/moderation/brands/{brand_id}/approve", headers=mod_headers
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["body"]["moderation_status"] == "approved"

    # GET /api/v1/brands lists the active brand
    list_res = await client.get("/api/v1/brands")
    assert list_res.status_code == 200
    brands_list = list_res.json()["body"]
    assert any(b["id"] == brand_id for b in brands_list)

    # GET /api/v1/brands/{slug} returns the brand
    get_res = await client.get("/api/v1/brands/synapse-clothing")
    assert get_res.status_code == 200
    assert get_res.json()["body"]["id"] == brand_id

    # Representative can upload brand logo
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    logo_res = await client.post(
        f"/api/v1/brands/{brand_id}/logo",
        headers=creator_headers,
        files={"file": ("logo.png", fake_png, "image/png")},
    )
    assert logo_res.status_code == 200
    assert logo_res.json()["body"]["logo_url"] is not None


async def test_brand_members_and_moderator_boundaries(
    client: AsyncClient, auth_headers
):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    # Register creator, moderator, and stranger
    reg_creator = await client.post(
        "/api/v1/auth/register",
        json={"login": "nova_creator", "password": "Password123!"},
    )
    creator_id = UUID(reg_creator.json()["body"]["user"]["id"])
    creator_headers = auth_headers(
        creator_id, permissions=["creator:brand", "creator:products", "catalog:manage"]
    )

    reg_mod = await client.post(
        "/api/v1/auth/register",
        json={"login": "nova_mod", "password": "Password123!"},
    )
    mod_id = UUID(reg_mod.json()["body"]["user"]["id"])
    mod_headers = auth_headers(mod_id, permissions=["creator:products"])

    reg_stranger = await client.post(
        "/api/v1/auth/register",
        json={"login": "nova_stranger", "password": "Password123!"},
    )
    stranger_id = UUID(reg_stranger.json()["body"]["user"]["id"])
    stranger_headers = auth_headers(stranger_id, permissions=["creator:products"])

    async with user_uow:
        c_user = await user_uow.users.get_by_id(creator_id)
        assert c_user is not None
        c_user.global_permissions = [
            "creator:brand",
            "creator:products",
            "catalog:manage",
        ]
        await user_uow.users.update(c_user)

        m_user = await user_uow.users.get_by_id(mod_id)
        assert m_user is not None
        m_user.global_permissions = ["creator:products"]
        await user_uow.users.update(m_user)

        s_user = await user_uow.users.get_by_id(stranger_id)
        assert s_user is not None
        s_user.global_permissions = ["creator:products"]
        await user_uow.users.update(s_user)

        await user_uow.commit()

    # Creator creates category
    cat_res = await client.post(
        "/api/v1/categories",
        headers=creator_headers,
        json={"name": "Streetwear", "slug": "streetwear"},
    )
    category_id = cat_res.json()["body"]["id"]

    # Creator creates brand
    brand_res = await client.post(
        "/api/v1/brands",
        headers=creator_headers,
        json={"name": "Nova Wear"},
    )
    assert brand_res.status_code == 201
    brand_id = brand_res.json()["body"]["id"]

    # Creator adds nova_mod as brand moderator
    add_mod_res = await client.post(
        f"/api/v1/brands/{brand_id}/members",
        headers=creator_headers,
        json={"login": "nova_mod", "role": "moderator"},
    )
    assert add_mod_res.status_code == 201
    assert add_mod_res.json()["body"]["role"] == "moderator"

    # Moderator can view members
    mod_members_res = await client.get(
        f"/api/v1/brands/{brand_id}/members",
        headers=mod_headers,
    )
    assert mod_members_res.status_code == 200
    members = mod_members_res.json()["body"]
    assert len(members) == 2

    # Moderator forbidden from updating brand profile
    patch_forbidden = await client.patch(
        f"/api/v1/brands/{brand_id}",
        headers=mod_headers,
        json={"name": "Hacked Nova"},
    )
    assert patch_forbidden.status_code == 403

    # Moderator forbidden from uploading logo
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    logo_forbidden = await client.post(
        f"/api/v1/brands/{brand_id}/logo",
        headers=mod_headers,
        files={"file": ("logo.png", fake_png, "image/png")},
    )
    assert logo_forbidden.status_code == 403

    # Moderator forbidden from deleting brand
    del_forbidden = await client.delete(
        f"/api/v1/brands/{brand_id}",
        headers=mod_headers,
    )
    assert del_forbidden.status_code == 403

    # Moderator forbidden from adding members
    add_member_forbidden = await client.post(
        f"/api/v1/brands/{brand_id}/members",
        headers=mod_headers,
        json={"login": "nova_stranger", "role": "moderator"},
    )
    assert add_member_forbidden.status_code == 403

    # Moderator forbidden from removing another member
    remove_other_forbidden = await client.delete(
        f"/api/v1/brands/{brand_id}/members/{creator_id}",
        headers=mod_headers,
    )
    assert remove_other_forbidden.status_code == 403

    # Stranger (non-member) cannot create product under this brand
    stranger_prod = await client.post(
        "/api/v1/products",
        headers=stranger_headers,
        json={
            "category_id": category_id,
            "title": "Stranger Product",
            "slug": "stranger-product",
            "base_price": 2000.0,
            "brand_id": brand_id,
        },
    )
    assert stranger_prod.status_code == 403

    # Brand moderator CAN create product under this brand
    mod_prod = await client.post(
        "/api/v1/products",
        headers=mod_headers,
        json={
            "category_id": category_id,
            "title": "Nova Cargo Pants",
            "slug": "nova-cargo-pants",
            "base_price": 5000.0,
            "brand_id": brand_id,
        },
    )
    assert mod_prod.status_code == 201
    prod_data = mod_prod.json()["body"]
    prod_id = prod_data["id"]
    assert prod_data["brand_id"] == brand_id
    assert prod_data["brand"] == "Nova Wear"
    assert prod_data["brand_slug"] == "nova-wear"

    # Brand moderator CAN update the product
    mod_update_prod = await client.patch(
        f"/api/v1/products/{prod_id}",
        headers=mod_headers,
        json={"title": "Nova Cargo Pants Pro"},
    )
    assert mod_update_prod.status_code == 200
    assert mod_update_prod.json()["body"]["title"] == "Nova Cargo Pants Pro"

    # Stranger cannot update product of the brand
    stranger_update = await client.patch(
        f"/api/v1/products/{prod_id}",
        headers=stranger_headers,
        json={"title": "Vandalized Pants"},
    )
    assert stranger_update.status_code == 403


async def test_brand_delisting_and_cascade_behavior(client: AsyncClient, auth_headers):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    # Register admin (catalog manager & mod approver), creator, buyer
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "echo_admin", "password": "Password123!"},
    )
    admin_id = UUID(reg_admin.json()["body"]["user"]["id"])
    admin_headers = auth_headers(
        admin_id, permissions=["catalog:manage", "mod:approve_manager", "*"]
    )

    reg_creator = await client.post(
        "/api/v1/auth/register",
        json={"login": "echo_creator", "password": "Password123!"},
    )
    creator_id = UUID(reg_creator.json()["body"]["user"]["id"])
    creator_headers = auth_headers(
        creator_id, permissions=["creator:brand", "creator:products"]
    )

    reg_buyer = await client.post(
        "/api/v1/auth/register",
        json={"login": "echo_buyer", "password": "Password123!"},
    )
    buyer_id = UUID(reg_buyer.json()["body"]["user"]["id"])
    buyer_headers = auth_headers(buyer_id)

    async with user_uow:
        a_user = await user_uow.users.get_by_id(admin_id)
        assert a_user is not None
        a_user.global_permissions = ["*", "catalog:manage", "mod:approve_manager"]
        await user_uow.users.update(a_user)

        c_user = await user_uow.users.get_by_id(creator_id)
        assert c_user is not None
        c_user.global_permissions = ["creator:brand", "creator:products"]
        await user_uow.users.update(c_user)

        await user_uow.commit()

    # 1. Setup category, brand, product, variant, address
    cat_res = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Apparel", "slug": "apparel"},
    )
    category_id = cat_res.json()["body"]["id"]

    brand_res = await client.post(
        "/api/v1/brands",
        headers=creator_headers,
        json={"name": "Echo Lab"},
    )
    brand_id = brand_res.json()["body"]["id"]

    await client.post(
        f"/api/v1/moderation/brands/{brand_id}/approve",
        headers=admin_headers,
    )

    prod_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": category_id,
            "title": "Echo Oversized Tee",
            "slug": "echo-oversized-tee",
            "base_price": 3000.0,
            "brand_id": brand_id,
            "is_published": True,
        },
    )
    prod_id = prod_res.json()["body"]["id"]

    var_res = await client.post(
        f"/api/v1/products/{prod_id}/variants",
        headers=creator_headers,
        json={
            "sku": "ECHO-TEE-BLK-L",
            "size": "L",
            "color_name": "Black",
            "stock_quantity": 10,
        },
    )
    variant_id = var_res.json()["body"]["id"]

    # Admin approves product
    approve_res = await client.post(
        f"/api/v1/moderation/products/{prod_id}/approve",
        headers=admin_headers,
    )
    assert approve_res.status_code == 200

    # Product appears in catalog and search
    cat_list = await client.get("/api/v1/products")
    assert any(p["id"] == prod_id for p in cat_list.json()["body"])

    search_res = await client.get("/api/v1/search?q=Echo")
    assert any(p["id"] == prod_id for p in search_res.json()["body"]["products"])

    # Buyer adds product to cart
    add_cart = await client.put(
        f"/api/v1/cart/items/{variant_id}",
        headers=buyer_headers,
        json={"quantity": 1},
    )
    assert add_cart.status_code == 200

    # Buyer sets up delivery address
    addr_res = await client.post(
        "/api/v1/users/me/addresses",
        headers=buyer_headers,
        json={
            "city": "Berlin",
            "street": "Alexanderplatz 1",
            "postal_code": "10178",
            "is_default": True,
        },
    )
    address_id = addr_res.json()["body"]["id"]

    # =========================================================================
    # Creator removes self from brand (sole representative -> brand is delisted)
    # =========================================================================
    delist_res = await client.delete(
        f"/api/v1/brands/{brand_id}/members/{creator_id}",
        headers=creator_headers,
    )
    assert delist_res.status_code == 200
    assert delist_res.json()["body"]["removed"] is True
    assert delist_res.json()["body"]["brand_deleted"] is True

    # 1. Brand disappears from active brands list
    active_brands = await client.get("/api/v1/brands")
    assert not any(b["id"] == brand_id for b in active_brands.json()["body"])

    # 2. Product disappears from public catalog
    catalog_after = await client.get("/api/v1/products")
    assert not any(p["id"] == prod_id for p in catalog_after.json()["body"])

    # 3. Product disappears from search
    search_after = await client.get("/api/v1/search?q=Echo")
    assert not any(p["id"] == prod_id for p in search_after.json()["body"]["products"])

    # 4. Direct link by slug works, but has brand_is_deleted=True
    slug_res = await client.get("/api/v1/products/echo-oversized-tee")
    assert slug_res.status_code == 200
    assert slug_res.json()["body"]["product"]["brand_is_deleted"] is True

    # 5. Adding to cart is forbidden
    re_add = await client.put(
        f"/api/v1/cart/items/{variant_id}",
        headers=buyer_headers,
        json={"quantity": 2},
    )
    assert re_add.status_code == 422
    assert (
        "Заказ невозможен, бренд снялся с продажи"
        in re_add.json()["errors"][0]["detail"]
    )

    # 6. Existing item in cart marked as is_available=False
    cart_after = await client.get("/api/v1/cart", headers=buyer_headers)
    assert cart_after.status_code == 200
    cart_items = cart_after.json()["body"]["items"]
    assert len(cart_items) == 1
    assert cart_items[0]["is_available"] is False

    # 7. Checkout fails with error message
    checkout_res = await client.post(
        "/api/v1/orders/checkout",
        headers=buyer_headers,
        json={"address_id": address_id},
    )
    assert checkout_res.status_code == 422
    assert (
        "Заказ невозможен, бренд снялся с продажи"
        in checkout_res.json()["errors"][0]["detail"]
    )


async def test_brand_name_update_syncs_products(client: AsyncClient, auth_headers):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    reg_creator = await client.post(
        "/api/v1/auth/register",
        json={"login": "apex_creator", "password": "Password123!"},
    )
    creator_id = UUID(reg_creator.json()["body"]["user"]["id"])
    creator_headers = auth_headers(
        creator_id, permissions=["creator:brand", "creator:products", "catalog:manage"]
    )

    async with user_uow:
        c_user = await user_uow.users.get_by_id(creator_id)
        assert c_user is not None
        c_user.global_permissions = [
            "creator:brand",
            "creator:products",
            "catalog:manage",
        ]
        await user_uow.users.update(c_user)
        await user_uow.commit()

    cat_res = await client.post(
        "/api/v1/categories",
        headers=creator_headers,
        json={"name": "Sportswear", "slug": "sportswear"},
    )
    category_id = cat_res.json()["body"]["id"]

    brand_res = await client.post(
        "/api/v1/brands",
        headers=creator_headers,
        json={"name": "Apex Corp"},
    )
    brand_id = brand_res.json()["body"]["id"]

    prod_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": category_id,
            "title": "Apex Performance Hoodie",
            "slug": "apex-performance-hoodie",
            "base_price": 4500.0,
            "brand_id": brand_id,
            "is_published": True,
        },
    )
    assert prod_res.status_code == 201

    # Update brand name
    update_res = await client.patch(
        f"/api/v1/brands/{brand_id}",
        headers=creator_headers,
        json={"name": "Apex Studio"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["body"]["name"] == "Apex Studio"
    assert update_res.json()["body"]["slug"] == "apex-studio"

    # Product detail reflects updated brand name
    prod_detail = await client.get(
        "/api/v1/products/apex-performance-hoodie",
        headers=creator_headers,
    )
    assert prod_detail.status_code == 200
    assert prod_detail.json()["body"]["product"]["brand"] == "Apex Studio"
    assert prod_detail.json()["body"]["product"]["brand_slug"] == "apex-studio"


async def test_self_removal_by_moderator(client: AsyncClient, auth_headers):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    reg_creator = await client.post(
        "/api/v1/auth/register",
        json={"login": "owner_creator", "password": "Password123!"},
    )
    creator_id = UUID(reg_creator.json()["body"]["user"]["id"])
    creator_headers = auth_headers(
        creator_id, permissions=["creator:brand", "creator:products"]
    )

    reg_mod = await client.post(
        "/api/v1/auth/register",
        json={"login": "helper_mod", "password": "Password123!"},
    )
    mod_id = UUID(reg_mod.json()["body"]["user"]["id"])
    mod_headers = auth_headers(mod_id)

    async with user_uow:
        c_user = await user_uow.users.get_by_id(creator_id)
        assert c_user is not None
        c_user.global_permissions = ["creator:brand", "creator:products"]
        await user_uow.users.update(c_user)
        await user_uow.commit()

    brand_res = await client.post(
        "/api/v1/brands",
        headers=creator_headers,
        json={"name": "Helper Brand"},
    )
    brand_id = brand_res.json()["body"]["id"]

    # Add helper_mod as moderator
    await client.post(
        f"/api/v1/brands/{brand_id}/members",
        headers=creator_headers,
        json={"login": "helper_mod", "role": "moderator"},
    )

    # Moderator removes self
    self_remove_res = await client.delete(
        f"/api/v1/brands/{brand_id}/members/{mod_id}",
        headers=mod_headers,
    )
    assert self_remove_res.status_code == 200
    assert self_remove_res.json()["body"]["removed"] is True
    # Representative is still active, brand is NOT deleted
    assert self_remove_res.json()["body"]["brand_deleted"] is False

    # Check members list
    members_res = await client.get(
        f"/api/v1/brands/{brand_id}/members",
        headers=creator_headers,
    )
    assert len(members_res.json()["body"]) == 1
    assert members_res.json()["body"][0]["user_id"] == str(creator_id)
