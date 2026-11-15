from uuid import UUID

import pytest

from src.api.dependencies import get_user_uow

pytestmark = pytest.mark.anyio


async def test_search_3_in_1_endpoint(client):
    # 1. Register admin and grant catalog:manage
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "login": "search_admin",
            "password": "Password123!",
        },
    )
    admin_id = reg.json()["body"]["user"]["id"]

    uow_factory = client._transport.app.dependency_overrides[get_user_uow]
    uow = uow_factory()
    async with uow:
        admin = await uow.users.get_by_id(UUID(admin_id))
        admin.global_permissions = ["catalog:manage"]
        await uow.users.update(admin)
        await uow.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "search_admin", "password": "Password123!"},
    )
    token = login.json()["body"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Setup category, products and variants
    cat_res = await client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "Clothing", "slug": "clothing"},
    )
    cat_id = cat_res.json()["body"]["id"]

    # Product 1: Nike Air Max
    p1 = await client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "category_id": cat_id,
            "title": "Nike Air Max",
            "slug": "nike-air-max",
            "brand": "Nike",
            "base_price": "150.00",
            "is_published": True,
        },
    )
    p1_id = p1.json()["body"]["id"]
    await client.post(
        f"/api/v1/products/{p1_id}/variants",
        headers=headers,
        json={
            "sku": "AIR-MAX-42-BLK",
            "size": "42",
            "color_name": "Black",
            "stock_quantity": 10,
        },
    )

    # Product 2: Nike Windrunner
    p2 = await client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "category_id": cat_id,
            "title": "Nike Windrunner Jacket",
            "slug": "nike-windrunner",
            "brand": "Nike",
            "base_price": "90.00",
            "is_published": True,
        },
    )
    p2_id = p2.json()["body"]["id"]
    await client.post(
        f"/api/v1/products/{p2_id}/variants",
        headers=headers,
        json={
            "sku": "WIND-JKT-L",
            "size": "L",
            "color_name": "Red",
            "stock_quantity": 5,
        },
    )

    # Product 3: Adidas Ultraboost
    p3 = await client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "category_id": cat_id,
            "title": "Adidas Ultraboost Light",
            "slug": "adidas-ultraboost",
            "brand": "Adidas",
            "base_price": "180.00",
            "is_published": True,
        },
    )
    p3_id = p3.json()["body"]["id"]
    await client.post(
        f"/api/v1/products/{p3_id}/variants",
        headers=headers,
        json={
            "sku": "UB-LIGHT-43-WHT",
            "size": "43",
            "color_name": "White",
            "stock_quantity": 8,
        },
    )

    # 3. Search by brand name "Nike"
    res_brand = await client.get("/api/v1/search?q=Nike")
    assert res_brand.status_code == 200
    data_brand = res_brand.json()["body"]

    # Check products
    product_titles = [p["title"] for p in data_brand["products"]]
    assert "Nike Air Max" in product_titles
    assert "Nike Windrunner Jacket" in product_titles

    # Check brands aggregation (Nike has 2 products)
    brand_map = {b["name"]: b["products_count"] for b in data_brand["brands"]}
    assert "Nike" in brand_map
    assert brand_map["Nike"] == 2

    # 4. Search by variant SKU "AIR-MAX"
    res_sku = await client.get("/api/v1/search?q=AIR-MAX")
    assert res_sku.status_code == 200
    data_sku = res_sku.json()["body"]
    assert len(data_sku["variants"]) >= 1
    assert data_sku["variants"][0]["sku"] == "AIR-MAX-42-BLK"

    # 5. Search by product title substring "Ultraboost"
    res_title = await client.get("/api/v1/search?q=Ultraboost")
    assert res_title.status_code == 200
    data_title = res_title.json()["body"]
    assert len(data_title["products"]) == 1
    assert data_title["products"][0]["title"] == "Adidas Ultraboost Light"

    # 6. Validation checks on search query length
    short_res = await client.get("/api/v1/search?q=a")
    assert short_res.status_code == 422
