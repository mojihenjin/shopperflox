import io
from uuid import UUID

import pytest

from src.api.dependencies import get_user_uow


@pytest.mark.anyio
async def test_creator_product_creation_and_permission_boundaries(client):
    # 1. Register admin, creator1, creator2, regular user
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "admin_user", "password": "Password123!"},
    )
    admin_id = reg_admin.json()["body"]["user"]["id"]

    reg_creator1 = await client.post(
        "/api/v1/auth/register",
        json={"login": "creator_one", "password": "Password123!"},
    )
    creator1_id = reg_creator1.json()["body"]["user"]["id"]

    reg_creator2 = await client.post(
        "/api/v1/auth/register",
        json={"login": "creator_two", "password": "Password123!"},
    )
    creator2_id = reg_creator2.json()["body"]["user"]["id"]

    reg_regular = await client.post(
        "/api/v1/auth/register",
        json={"login": "regular_user", "password": "Password123!"},
    )
    assert reg_regular.status_code == 201

    # Assign permissions
    uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)
    uow = uow_factory()
    async with uow:
        admin = await uow.users.get_by_id(UUID(admin_id))
        admin.global_permissions = ["catalog:manage", "mod:approve_manager"]
        await uow.users.update(admin)

        c1 = await uow.users.get_by_id(UUID(creator1_id))
        c1.global_permissions = ["creator:products"]
        await uow.users.update(c1)

        c2 = await uow.users.get_by_id(UUID(creator2_id))
        c2.global_permissions = ["creator:drops"]
        await uow.users.update(c2)

        await uow.commit()

    # Login all actors
    res_admin = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin_user", "password": "Password123!"},
    )
    admin_headers = {
        "Authorization": f"Bearer {res_admin.json()['body']['access_token']}"
    }

    res_c1 = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "creator_one", "password": "Password123!"},
    )
    c1_headers = {"Authorization": f"Bearer {res_c1.json()['body']['access_token']}"}

    res_c2 = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "creator_two", "password": "Password123!"},
    )
    c2_headers = {"Authorization": f"Bearer {res_c2.json()['body']['access_token']}"}

    res_reg = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "regular_user", "password": "Password123!"},
    )
    reg_headers = {"Authorization": f"Bearer {res_reg.json()['body']['access_token']}"}

    # Admin creates category
    cat_res = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Creator Streetwear", "slug": "creator-streetwear"},
    )
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["body"]["id"]

    # 2. Regular user cannot create product -> 403
    forbidden_prod = await client.post(
        "/api/v1/products",
        headers=reg_headers,
        json={
            "category_id": cat_id,
            "title": "Unauthorized Tee",
            "slug": "unauthorized-tee",
            "base_price": 1000,
        },
    )
    assert forbidden_prod.status_code == 403

    # 3. Creator1 creates product with self-worked, multi-currency, characteristics, and variants
    create_prod_res = await client.post(
        "/api/v1/products",
        headers=c1_headers,
        json={
            "category_id": cat_id,
            "title": "Cyberpunk Heavy Hoodie",
            "slug": "cyberpunk-heavy-hoodie",
            "is_self_worked": True,
            "base_price": 4500.00,
            "price_usd": 49.99,
            "price_eur": 45.50,
            "material": "100% French Terry Cotton",
            "density": "460 g/m²",
            "composition": "Cotton 100%",
            "print_method": "Silk Screen + Distressed Wash",
            "note": "Oversized fit. Hand-dyed in small batches.",
            "description": "Exclusive author drop.",
            "is_published": True,
            "variants": [
                {
                    "color": "Acid Black",
                    "color_hex": "#1a1a1a",
                    "size": "L",
                    "stock_quantity": 20,
                    # sku omitted to verify auto-generation
                },
                {
                    "color": "Ghost White",
                    "color_hex": "#fafafa",
                    "size": "XL",
                    "stock_quantity": 10,
                    "sku": "CYBER-HOOD-WHT-XL",
                    "price_override": 4700.00,
                },
            ],
        },
    )
    assert create_prod_res.status_code == 201
    prod_data = create_prod_res.json()["body"]
    prod_id = prod_data["id"]

    assert prod_data["creator_id"] == creator1_id
    assert prod_data["brand"] == "self-worked"  # defaulted because is_self_worked=True
    assert prod_data["is_self_worked"] is True
    assert float(prod_data["base_price"]) == 4500.00
    assert float(prod_data["price_usd"]) == 49.99
    assert float(prod_data["price_eur"]) == 45.50
    assert prod_data["material"] == "100% French Terry Cotton"
    assert prod_data["density"] == "460 g/m²"
    assert prod_data["composition"] == "Cotton 100%"
    assert prod_data["print_method"] == "Silk Screen + Distressed Wash"
    assert prod_data["note"] == "Oversized fit. Hand-dyed in small batches."

    # 4. Creator1 adds images (including color-bound image and uploaded file)
    img_res = await client.post(
        f"/api/v1/products/{prod_id}/images",
        headers=c1_headers,
        json={
            "url": "https://cdn.example.com/cyber-black.jpg",
            "color": "Acid Black",
            "alt_text": "Acid Black Front",
            "sort_order": 1,
            "is_main": True,
        },
    )
    assert img_res.status_code == 201
    assert img_res.json()["body"]["color"] == "Acid Black"
    assert img_res.json()["body"]["is_main"] is True

    # Upload an image file as creator1
    fake_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    upload_res = await client.post(
        f"/api/v1/products/{prod_id}/images/upload",
        headers=c1_headers,
        files={"file": ("hoodie_white.png", io.BytesIO(fake_png), "image/png")},
        data={"color": "Ghost White", "sort_order": "2", "is_main": "false"},
    )
    assert upload_res.status_code == 201
    assert upload_res.json()["body"]["color"] == "Ghost White"

    # 5. Creator2 (unrelated creator) tries to modify creator1's product -> 403 Forbidden
    patch_forbidden = await client.patch(
        f"/api/v1/products/{prod_id}",
        headers=c2_headers,
        json={"title": "Hacked Title"},
    )
    assert patch_forbidden.status_code == 403

    img_forbidden = await client.post(
        f"/api/v1/products/{prod_id}/images",
        headers=c2_headers,
        json={"url": "https://cdn.example.com/hack.jpg"},
    )
    assert img_forbidden.status_code == 403

    upload_forbidden = await client.post(
        f"/api/v1/products/{prod_id}/images/upload",
        headers=c2_headers,
        files={"file": ("hack.png", io.BytesIO(fake_png), "image/png")},
    )
    assert upload_forbidden.status_code == 403

    variant_forbidden = await client.post(
        f"/api/v1/products/{prod_id}/variants",
        headers=c2_headers,
        json={"sku": "HACK-SKU", "stock_quantity": 5},
    )
    assert variant_forbidden.status_code == 403

    delete_forbidden = await client.delete(
        f"/api/v1/products/{prod_id}",
        headers=c2_headers,
    )
    assert delete_forbidden.status_code == 403

    # 6. Creator1 can update their own product
    patch_c1 = await client.patch(
        f"/api/v1/products/{prod_id}",
        headers=c1_headers,
        json={
            "title": "Cyberpunk Heavy Hoodie (V2)",
            "price_usd": 54.99,
            "material": "100% Heavy French Terry",
        },
    )
    assert patch_c1.status_code == 200
    assert patch_c1.json()["body"]["title"] == "Cyberpunk Heavy Hoodie (V2)"
    assert float(patch_c1.json()["body"]["price_usd"]) == 54.99
    assert patch_c1.json()["body"]["material"] == "100% Heavy French Terry"

    # 7. Admin (catalog:manage) CAN modify creator's product
    patch_admin = await client.patch(
        f"/api/v1/products/{prod_id}",
        headers=admin_headers,
        json={"note": "Verified by Admin team."},
    )
    assert patch_admin.status_code == 200
    assert patch_admin.json()["body"]["note"] == "Verified by Admin team."

    # Approve product via moderation
    approve_res = await client.post(
        f"/api/v1/moderation/products/{prod_id}/approve",
        headers=admin_headers,
    )
    assert approve_res.status_code == 200

    # 8. Check product detail public endpoint
    detail_res = await client.get("/api/v1/products/cyberpunk-heavy-hoodie")
    assert detail_res.status_code == 200
    detail = detail_res.json()["body"]
    assert detail["product"]["id"] == prod_id
    assert detail["product"]["creator_id"] == creator1_id
    assert detail["product"]["is_self_worked"] is True
    assert len(detail["variants"]) == 2

    # Check that auto-generated SKU was set
    skus = [v["sku"] for v in detail["variants"]]
    assert "CYBER-HOOD-WHT-XL" in skus
    auto_sku = [s for s in skus if s != "CYBER-HOOD-WHT-XL"][0]
    assert len(auto_sku) > 0

    # Check images and color tags
    assert len(detail["images"]) == 2
    colors = {img["color"] for img in detail["images"]}
    assert colors == {"Acid Black", "Ghost White"}
