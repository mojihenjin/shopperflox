from uuid import UUID

import pytest

from src.api.dependencies import get_user_uow


@pytest.mark.anyio
async def test_full_catalog_and_favorites_flow(client):
    # 1. Register admin user and regular user
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={
            "login": "catalog_admin",
            "password": "Password123!",
        },
    )
    admin_id = reg_admin.json()["body"]["user"]["id"]

    reg_user = await client.post(
        "/api/v1/auth/register",
        json={
            "login": "catalog_user",
            "password": "Password123!",
        },
    )
    assert reg_user.status_code == 201

    # Grant catalog:manage to admin
    uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)
    uow = uow_factory()
    async with uow:
        admin = await uow.users.get_by_id(UUID(admin_id))
        admin.global_permissions = ["catalog:manage", "mod:approve_manager"]
        await uow.users.update(admin)
        await uow.commit()

    # Login admin
    login_admin = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "catalog_admin", "password": "Password123!"},
    )
    admin_token = login_admin.json()["body"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Login regular user
    login_user = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "catalog_user", "password": "Password123!"},
    )
    user_token = login_user.json()["body"]["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 2. Regular user tries admin action -> 403 Forbidden
    forbidden_cat = await client.post(
        "/api/v1/categories",
        headers=user_headers,
        json={"name": "Hats", "slug": "hats"},
    )
    assert forbidden_cat.status_code == 403

    # 3. Admin creates category
    create_cat = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Apparel", "slug": "apparel", "sort_order": 1},
    )
    assert create_cat.status_code == 201
    cat_id = create_cat.json()["body"]["id"]

    # 4. Public list categories
    list_cats = await client.get("/api/v1/categories")
    assert list_cats.status_code == 200
    assert len(list_cats.json()["body"]) == 1
    assert list_cats.json()["body"][0]["slug"] == "apparel"

    # 5. Admin creates product
    create_prod = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "category_id": cat_id,
            "title": "Cool Hoodie",
            "slug": "cool-hoodie",
            "base_price": 59.99,
            "description": "Warm and stylish hoodie",
            "attributes": {"material": "cotton"},
            "is_published": True,
        },
    )
    assert create_prod.status_code == 201
    prod_id = create_prod.json()["body"]["id"]

    # 6. Admin creates variant
    create_var = await client.post(
        f"/api/v1/products/{prod_id}/variants",
        headers=admin_headers,
        json={
            "sku": "HOODIE-M-BLK",
            "size": "M",
            "color_name": "Black",
            "color_hex": "#000000",
            "stock_quantity": 25,
        },
    )
    assert create_var.status_code == 201
    var_id = create_var.json()["body"]["id"]

    # Update variant
    patch_var = await client.patch(
        f"/api/v1/variants/{var_id}",
        headers=admin_headers,
        json={"stock_quantity": 30},
    )
    assert patch_var.status_code == 200
    assert patch_var.json()["body"]["stock_quantity"] == 30

    # 7. Admin adds image
    create_img = await client.post(
        f"/api/v1/products/{prod_id}/images",
        headers=admin_headers,
        json={
            "url": "https://cdn.example.com/hoodie-front.jpg",
            "variant_id": var_id,
            "is_main": True,
        },
    )
    assert create_img.status_code == 201
    assert create_img.json()["body"]["is_main"] is True

    # Approve product via moderation
    approve_res = await client.post(
        f"/api/v1/moderation/products/{prod_id}/approve",
        headers=admin_headers,
    )
    assert approve_res.status_code == 200

    # 8. Public list products with pagination & metadata
    list_prods = await client.get("/api/v1/products?limit=10&offset=0")
    assert list_prods.status_code == 200
    assert len(list_prods.json()["body"]) == 1
    assert list_prods.json()["metadata"]["total"] == 1

    # 9. Public product detail
    detail = await client.get("/api/v1/products/cool-hoodie")
    assert detail.status_code == 200
    body = detail.json()["body"]
    assert body["product"]["slug"] == "cool-hoodie"
    assert len(body["variants"]) == 1
    assert len(body["images"]) == 1

    # 10. Favorites flow for regular user
    # Add to favorites
    add_fav = await client.post(
        f"/api/v1/favorites/{prod_id}",
        headers=user_headers,
    )
    assert add_fav.status_code == 201

    # List favorites
    list_fav = await client.get("/api/v1/favorites", headers=user_headers)
    assert list_fav.status_code == 200
    assert len(list_fav.json()["body"]) == 1
    assert list_fav.json()["body"][0]["id"] == prod_id
    assert list_fav.json()["metadata"]["total"] == 1

    # Remove from favorites
    del_fav = await client.delete(
        f"/api/v1/favorites/{prod_id}",
        headers=user_headers,
    )
    assert del_fav.status_code == 200

    list_fav_after = await client.get("/api/v1/favorites", headers=user_headers)
    assert len(list_fav_after.json()["body"]) == 0

    # 11. Admin updates and deletes product
    patch_prod = await client.patch(
        f"/api/v1/products/{prod_id}",
        headers=admin_headers,
        json={"title": "Updated Cool Hoodie"},
    )
    assert patch_prod.status_code == 200
    assert patch_prod.json()["body"]["title"] == "Updated Cool Hoodie"

    del_prod = await client.delete(
        f"/api/v1/products/{prod_id}",
        headers=admin_headers,
    )
    assert del_prod.status_code == 200

    # Detail after deletion returns 404
    detail_deleted = await client.get("/api/v1/products/cool-hoodie")
    assert detail_deleted.status_code == 404


@pytest.mark.anyio
async def test_cyrillic_variants_auto_sku_regression(client):
    # 1. Register admin
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={
            "login": "cyrillic_admin",
            "password": "Password123!",
        },
    )
    admin_id = reg_admin.json()["body"]["user"]["id"]

    uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)
    uow = uow_factory()
    async with uow:
        admin = await uow.users.get_by_id(UUID(admin_id))
        admin.global_permissions = ["catalog:manage", "mod:approve_manager"]
        await uow.users.update(admin)
        await uow.commit()

    login_admin = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "cyrillic_admin", "password": "Password123!"},
    )
    admin_token = login_admin.json()["body"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Create category
    create_cat = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Платья", "slug": "platya"},
    )
    assert create_cat.status_code == 201
    cat_id = create_cat.json()["body"]["id"]

    # 3. Create product with two cyrillic colors and same cyrillic size without sku
    create_prod = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "category_id": cat_id,
            "title": "Шелковое платье",
            "slug": "shelkovoe-platye",
            "base_price": 5000.0,
            "is_published": True,
            "variants": [
                {
                    "color": "ЛЕОПАРДОВЫЙ",
                    "size": "МАЛЕНЬКИЙ",
                    "stock_quantity": 5,
                },
                {
                    "color": "РОЗОВЫЙ",
                    "size": "МАЛЕНЬКИЙ",
                    "stock_quantity": 10,
                },
            ],
        },
    )
    assert create_prod.status_code == 201
    prod_data = create_prod.json()["body"]
    prod_id = prod_data["id"]

    # Approve product to check detail
    await client.post(
        f"/api/v1/moderation/products/{prod_id}/approve",
        headers=admin_headers,
    )

    detail_res = await client.get("/api/v1/products/shelkovoe-platye")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()["body"]
    variants = detail_data["variants"]
    assert len(variants) == 2

    sku1 = variants[0]["sku"]
    sku2 = variants[1]["sku"]
    assert sku1 != sku2
    assert len(sku1) > 0
    assert len(sku2) > 0
    assert any("LEOPARD" in s for s in (sku1, sku2))
    assert any("ROZOV" in s for s in (sku1, sku2))

    # 4. Also verify duplicate explicit SKUs in a batch are rejected with 422
    dup_res = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "category_id": cat_id,
            "title": "Дубликат SKU",
            "slug": "dublikat-sku",
            "base_price": 1000.0,
            "variants": [
                {"sku": "DUP-SKU-1", "color": "Красный", "size": "M"},
                {"sku": "DUP-SKU-1", "color": "Синий", "size": "L"},
            ],
        },
    )
    assert dup_res.status_code == 422
