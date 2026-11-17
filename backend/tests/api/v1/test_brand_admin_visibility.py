from uuid import UUID

import pytest

from src.api.dependencies import get_user_uow


@pytest.mark.anyio
async def test_admin_brand_restore_and_visibility_override(client):
    # 1. Register admin, creator, buyer
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "brand_admin", "password": "Password123!"},
    )
    admin_id = reg_admin.json()["body"]["user"]["id"]

    reg_creator = await client.post(
        "/api/v1/auth/register",
        json={"login": "brand_owner", "password": "Password123!"},
    )
    creator_id = reg_creator.json()["body"]["user"]["id"]

    reg_buyer = await client.post(
        "/api/v1/auth/register",
        json={"login": "brand_buyer", "password": "Password123!"},
    )
    _ = reg_buyer.json()["body"]["user"]["id"]

    # Assign permissions
    uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)
    uow = uow_factory()
    async with uow:
        admin = await uow.users.get_by_id(UUID(admin_id))
        admin.global_permissions = [
            "admin:access",
            "mod:approve_manager",
            "catalog:manage",
            "*",
        ]
        await uow.users.update(admin)

        c = await uow.users.get_by_id(UUID(creator_id))
        c.global_permissions = ["creator:brand", "creator:products"]
        await uow.users.update(c)
        await uow.commit()

    # Logins
    res_admin = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "brand_admin", "password": "Password123!"},
    )
    admin_headers = {
        "Authorization": f"Bearer {res_admin.json()['body']['access_token']}"
    }

    res_c = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "brand_owner", "password": "Password123!"},
    )
    creator_headers = {
        "Authorization": f"Bearer {res_c.json()['body']['access_token']}"
    }

    res_b = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "brand_buyer", "password": "Password123!"},
    )
    buyer_headers = {"Authorization": f"Bearer {res_b.json()['body']['access_token']}"}

    # Admin creates category
    cat_res = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Brand Cat", "slug": "brand-cat"},
    )
    cat_id = cat_res.json()["body"]["id"]

    # Creator creates brand
    brand_res = await client.post(
        "/api/v1/brands",
        headers=creator_headers,
        json={"name": "Aether Brand", "his_url": "https://aether.example.com"},
    )
    assert brand_res.status_code == 201
    brand_id = brand_res.json()["body"]["id"]

    # Admin approves brand
    app_brand = await client.post(
        f"/api/v1/moderation/brands/{brand_id}/approve",
        headers=admin_headers,
    )
    assert app_brand.status_code == 200

    # Creator creates product for this brand
    prod_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": cat_id,
            "brand_id": brand_id,
            "title": "Aether Jacket",
            "slug": "aether-jacket",
            "base_price": "250.00",
            "is_published": True,
            "variants": [
                {
                    "sku": "AETHER-J-1",
                    "size": "M",
                    "color_name": "Black",
                    "stock_quantity": 5,
                }
            ],
        },
    )
    assert prod_res.status_code == 201
    prod_id = prod_res.json()["body"]["id"]

    # Admin approves product
    app_prod = await client.post(
        f"/api/v1/moderation/products/{prod_id}/approve",
        headers=admin_headers,
    )
    assert app_prod.status_code == 200

    # Verify product appears in public catalog
    cat_list = await client.get("/api/v1/products")
    assert any(p["id"] == prod_id for p in cat_list.json()["body"])

    # Verify product detail page
    detail_res = await client.get("/api/v1/products/aether-jacket")
    assert detail_res.status_code == 200
    prod_data = detail_res.json()["body"]["product"]
    assert prod_data["is_hidden"] == 0
    assert prod_data["effective_hidden"] == 0

    # =========================================================================
    # Test 1: Set visibility override to 1 (direct link only)
    # =========================================================================
    # Non-admin rejected -> 403
    forbidden_vis = await client.patch(
        f"/api/v1/admin/brands/{brand_id}/visibility",
        headers=buyer_headers,
        json={"products_hidden_override": 1},
    )
    assert forbidden_vis.status_code == 403

    # Admin sets override = 1
    vis1_res = await client.patch(
        f"/api/v1/admin/brands/{brand_id}/visibility",
        headers=admin_headers,
        json={"products_hidden_override": 1},
    )
    assert vis1_res.status_code == 200
    assert vis1_res.json()["body"]["products_hidden_override"] == 1

    # Product disappears from public catalog
    cat_list_1 = await client.get("/api/v1/products")
    assert not any(p["id"] == prod_id for p in cat_list_1.json()["body"])

    # Product remains accessible by direct link
    detail_res_1 = await client.get("/api/v1/products/aether-jacket")
    assert detail_res_1.status_code == 200
    prod_data_1 = detail_res_1.json()["body"]["product"]
    assert prod_data_1["is_hidden"] == 0  # Original in DB NOT modified!
    assert prod_data_1["effective_hidden"] == 1  # Effective visibility is 1

    # =========================================================================
    # Test 2: Set visibility override to 2 (hidden everywhere)
    # =========================================================================
    vis2_res = await client.patch(
        f"/api/v1/admin/brands/{brand_id}/visibility",
        headers=admin_headers,
        json={"products_hidden_override": 2},
    )
    assert vis2_res.status_code == 200
    assert vis2_res.json()["body"]["products_hidden_override"] == 2

    # Product is absent from catalog
    cat_list_2 = await client.get("/api/v1/products")
    assert not any(p["id"] == prod_id for p in cat_list_2.json()["body"])

    # Public user receives 404 Not Found on direct link
    public_detail_2 = await client.get("/api/v1/products/aether-jacket")
    assert public_detail_2.status_code == 404

    # Creator and Admin can still access it
    creator_detail_2 = await client.get(
        "/api/v1/products/aether-jacket",
        headers=creator_headers,
    )
    assert creator_detail_2.status_code == 200
    assert creator_detail_2.json()["body"]["product"]["effective_hidden"] == 2
    assert creator_detail_2.json()["body"]["product"]["is_hidden"] == 0

    # =========================================================================
    # Test 3: Reset visibility override to null (restore original visibility)
    # =========================================================================
    vis_null_res = await client.patch(
        f"/api/v1/admin/brands/{brand_id}/visibility",
        headers=admin_headers,
        json={"products_hidden_override": None},
    )
    assert vis_null_res.status_code == 200
    assert vis_null_res.json()["body"]["products_hidden_override"] is None

    # Product is back in public catalog
    cat_list_reset = await client.get("/api/v1/products")
    assert any(p["id"] == prod_id for p in cat_list_reset.json()["body"])

    # Direct link works for public
    public_detail_reset = await client.get("/api/v1/products/aether-jacket")
    assert public_detail_reset.status_code == 200
    assert public_detail_reset.json()["body"]["product"]["effective_hidden"] == 0

    # Invalid override (e.g. 5) returns 422
    invalid_vis = await client.patch(
        f"/api/v1/admin/brands/{brand_id}/visibility",
        headers=admin_headers,
        json={"products_hidden_override": 5},
    )
    assert invalid_vis.status_code == 422

    # =========================================================================
    # Test 4: Brand restore
    # =========================================================================
    # Delete brand (soft delete)
    del_brand = await client.delete(
        f"/api/v1/brands/{brand_id}",
        headers=creator_headers,
    )
    assert del_brand.status_code == 200
    assert del_brand.json()["body"]["is_deleted"] is True

    # Non-admin tries to restore -> 403 Forbidden
    forbidden_restore = await client.post(
        f"/api/v1/admin/brands/{brand_id}/restore",
        headers=buyer_headers,
    )
    assert forbidden_restore.status_code == 403

    # Admin restores brand -> 200 OK
    admin_restore = await client.post(
        f"/api/v1/admin/brands/{brand_id}/restore",
        headers=admin_headers,
    )
    assert admin_restore.status_code == 200
    assert admin_restore.json()["body"]["is_deleted"] is False

    # Check active brands includes the restored brand
    active_brands = await client.get("/api/v1/brands")
    assert any(b["id"] == brand_id for b in active_brands.json()["body"])
