from uuid import UUID

import pytest
from httpx import AsyncClient

from src.api.dependencies import get_user_uow


@pytest.mark.anyio
async def test_product_visibility_matrix(client: AsyncClient):
    # 1. Register users: admin, creator, stranger, moderator
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "admin_vis", "password": "Password123!"},
    )
    admin_id = UUID(reg_admin.json()["body"]["user"]["id"])

    reg_creator = await client.post(
        "/api/v1/auth/register",
        json={"login": "creator_vis", "password": "Password123!"},
    )
    creator_id = UUID(reg_creator.json()["body"]["user"]["id"])

    reg_stranger = await client.post(
        "/api/v1/auth/register",
        json={"login": "stranger_vis", "password": "Password123!"},
    )
    assert reg_stranger.status_code == 201

    reg_mod = await client.post(
        "/api/v1/auth/register",
        json={"login": "mod_vis", "password": "Password123!"},
    )
    mod_id = UUID(reg_mod.json()["body"]["user"]["id"])

    # Setup permissions
    uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    uow = uow_factory()
    async with uow:
        admin = await uow.users.get_by_id(admin_id)
        admin.global_permissions = ["catalog:manage"]
        await uow.users.update(admin)

        creator = await uow.users.get_by_id(creator_id)
        creator.global_permissions = ["creator:products"]
        await uow.users.update(creator)

        moderator = await uow.users.get_by_id(mod_id)
        moderator.global_permissions = ["mod:update", "mod:approve_manager"]
        await uow.users.update(moderator)

        await uow.commit()

    # Log in all users
    async def get_auth_header(identifier: str):
        res = await client.post(
            "/api/v1/auth/login",
            json={"identifier": identifier, "password": "Password123!"},
        )
        token = res.json()["body"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    admin_headers = await get_auth_header("admin_vis")
    creator_headers = await get_auth_header("creator_vis")
    stranger_headers = await get_auth_header("stranger_vis")
    mod_headers = await get_auth_header("mod_vis")

    # 2. Admin creates category
    cat_res = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "VisCategory", "slug": "vis-category"},
    )
    assert cat_res.status_code == 201
    category_id = cat_res.json()["body"]["id"]

    # 3. Creator creates 3 products:
    # Prod 0: is_hidden=0 (public)
    # Prod 1: is_hidden=1 (hidden from catalog/search, accessible by direct slug)
    # Prod 2: is_hidden=2 (fully hidden, 404 for guests and strangers, 200 for creator & mod)
    prod0_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": category_id,
            "title": "Visible Jacket Zero",
            "slug": "vis-jacket-0",
            "base_price": 100.0,
            "is_published": True,
            "is_hidden": 0,
            "is_limited": False,
        },
    )
    assert prod0_res.status_code == 201
    assert prod0_res.json()["body"]["is_hidden"] == 0
    assert prod0_res.json()["body"]["is_limited"] is False

    prod1_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": category_id,
            "title": "Unlisted Jacket One",
            "slug": "vis-jacket-1",
            "base_price": 120.0,
            "is_published": True,
            "is_hidden": 1,
            "is_limited": True,
        },
    )
    assert prod1_res.status_code == 201
    assert prod1_res.json()["body"]["is_hidden"] == 1
    assert prod1_res.json()["body"]["is_limited"] is True

    prod2_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": category_id,
            "title": "Secret Jacket Two",
            "slug": "vis-jacket-2",
            "base_price": 150.0,
            "is_published": True,
            "is_hidden": 2,
            "is_limited": True,
        },
    )
    assert prod2_res.status_code == 201
    assert prod2_res.json()["body"]["is_hidden"] == 2
    assert prod2_res.json()["body"]["is_limited"] is True

    # Approve all three products via moderation
    for p_res in [prod0_res, prod1_res, prod2_res]:
        pid = p_res.json()["body"]["id"]
        app_res = await client.post(
            f"/api/v1/moderation/products/{pid}/approve",
            headers=mod_headers,
        )
        assert app_res.status_code == 200

    # ========================================================
    # Test 1: GET /api/v1/products (Catalog listing)
    # Only is_hidden=0 must be present!
    # ========================================================
    list_res = await client.get("/api/v1/products")
    assert list_res.status_code == 200
    listed_slugs = [p["slug"] for p in list_res.json()["body"]]
    assert "vis-jacket-0" in listed_slugs
    assert "vis-jacket-1" not in listed_slugs
    assert "vis-jacket-2" not in listed_slugs

    # ========================================================
    # Test 2: GET /api/v1/search (Search 3-in-1)
    # Only is_hidden=0 must be found!
    # ========================================================
    search_res = await client.get("/api/v1/search?q=Jacket")
    assert search_res.status_code == 200
    found_slugs = [p["slug"] for p in search_res.json()["body"]["products"]]
    assert "vis-jacket-0" in found_slugs
    assert "vis-jacket-1" not in found_slugs
    assert "vis-jacket-2" not in found_slugs

    # Search specifically for One and Two
    search_1 = await client.get("/api/v1/search?q=Unlisted")
    assert len(search_1.json()["body"]["products"]) == 0

    search_2 = await client.get("/api/v1/search?q=Secret")
    assert len(search_2.json()["body"]["products"]) == 0

    # ========================================================
    # Test 3: GET /api/v1/products/{slug} (Direct slug access)
    # ========================================================

    # Prod 0 (is_hidden=0): Accessible by unauthenticated guest
    d0 = await client.get("/api/v1/products/vis-jacket-0")
    assert d0.status_code == 200
    assert d0.json()["body"]["product"]["slug"] == "vis-jacket-0"

    # Prod 1 (is_hidden=1): Accessible by unauthenticated guest (closed drop)
    d1 = await client.get("/api/v1/products/vis-jacket-1")
    assert d1.status_code == 200
    assert d1.json()["body"]["product"]["slug"] == "vis-jacket-1"

    # Prod 2 (is_hidden=2):
    # - Unauthenticated guest -> 404
    d2_guest = await client.get("/api/v1/products/vis-jacket-2")
    assert d2_guest.status_code == 404

    # - Authenticated stranger without permissions -> 404
    d2_stranger = await client.get(
        "/api/v1/products/vis-jacket-2", headers=stranger_headers
    )
    assert d2_stranger.status_code == 404

    # - Creator of product -> 200
    d2_creator = await client.get(
        "/api/v1/products/vis-jacket-2", headers=creator_headers
    )
    assert d2_creator.status_code == 200
    assert d2_creator.json()["body"]["product"]["slug"] == "vis-jacket-2"

    # - Moderator with mod:update -> 200
    d2_mod = await client.get("/api/v1/products/vis-jacket-2", headers=mod_headers)
    assert d2_mod.status_code == 200
    assert d2_mod.json()["body"]["product"]["slug"] == "vis-jacket-2"

    # - Admin with catalog:manage -> 200
    d2_admin = await client.get("/api/v1/products/vis-jacket-2", headers=admin_headers)
    assert d2_admin.status_code == 200
    assert d2_admin.json()["body"]["product"]["slug"] == "vis-jacket-2"

    # ========================================================
    # Test 4: Update product is_hidden & is_limited
    # ========================================================
    prod2_id = prod2_res.json()["body"]["id"]

    # Creator changes is_hidden from 2 to 1 (closed drop)
    upd_res = await client.patch(
        f"/api/v1/products/{prod2_id}",
        headers=creator_headers,
        json={"is_hidden": 1, "is_limited": False},
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["body"]["is_hidden"] == 1
    assert upd_res.json()["body"]["is_limited"] is False

    # Now guest can access prod 2
    d2_guest_now = await client.get("/api/v1/products/vis-jacket-2")
    assert d2_guest_now.status_code == 200

    # Still absent from catalog
    list_res2 = await client.get("/api/v1/products")
    assert "vis-jacket-2" not in [p["slug"] for p in list_res2.json()["body"]]

    # Change to 0 (fully public)
    upd_res2 = await client.patch(
        f"/api/v1/products/{prod2_id}",
        headers=creator_headers,
        json={"is_hidden": 0},
    )
    assert upd_res2.status_code == 200
    assert upd_res2.json()["body"]["is_hidden"] == 0

    # Now present in catalog
    list_res3 = await client.get("/api/v1/products")
    assert "vis-jacket-2" in [p["slug"] for p in list_res3.json()["body"]]
