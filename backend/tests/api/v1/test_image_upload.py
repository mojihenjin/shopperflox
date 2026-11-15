import io
from uuid import UUID

import pytest

from src.api.dependencies import get_user_uow

pytestmark = pytest.mark.anyio


async def test_product_image_upload_and_validation(client):
    # 1. Register admin user
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "login": "image_admin",
            "password": "Password123!",
        },
    )
    admin_id = reg.json()["body"]["user"]["id"]

    # Grant catalog:manage
    uow_factory = client._transport.app.dependency_overrides[get_user_uow]
    uow = uow_factory()
    async with uow:
        admin = await uow.users.get_by_id(UUID(admin_id))
        admin.global_permissions = ["catalog:manage"]
        await uow.users.update(admin)
        await uow.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "image_admin", "password": "Password123!"},
    )
    token = login.json()["body"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create category and product
    cat_res = await client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "Shoes", "slug": "shoes"},
    )
    cat_id = cat_res.json()["body"]["id"]

    prod_res = await client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "category_id": cat_id,
            "title": "Sneakers",
            "slug": "sneakers",
            "brand": "Nike",
            "base_price": "120.00",
            "is_published": True,
        },
    )
    prod_id = prod_res.json()["body"]["id"]

    # 3. Upload valid PNG
    valid_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 30
    res_png = await client.post(
        f"/api/v1/products/{prod_id}/images/upload",
        headers=headers,
        files={"file": ("test.png", io.BytesIO(valid_png_bytes), "image/png")},
        data={"alt_text": "Sneakers Front", "is_main": "true"},
    )
    assert res_png.status_code == 201
    png_data = res_png.json()["body"]
    assert png_data["is_main"] is True
    assert png_data["url"].endswith(".png")

    # 4. Upload valid WebP
    valid_webp_bytes = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 20
    res_webp = await client.post(
        f"/api/v1/products/{prod_id}/images/upload",
        headers=headers,
        files={"file": ("photo.webp", io.BytesIO(valid_webp_bytes), "image/webp")},
    )
    assert res_webp.status_code == 201
    webp_data = res_webp.json()["body"]
    assert webp_data["url"].endswith(".webp")

    # 5. Reject fake exe / text file disguised as image/png
    fake_exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00This is a disguised binary file"
    res_fake = await client.post(
        f"/api/v1/products/{prod_id}/images/upload",
        headers=headers,
        files={"file": ("malicious.png", io.BytesIO(fake_exe_bytes), "image/png")},
    )
    assert res_fake.status_code == 422
    assert "unsupported image format" in res_fake.json()["errors"][0]["detail"].lower()

    # 6. Reject oversized file (> 5 MB)
    large_bytes = b"\x89PNG\r\n\x1a\n" + (b"\x00" * (5 * 1024 * 1024 + 50))
    res_large = await client.post(
        f"/api/v1/products/{prod_id}/images/upload",
        headers=headers,
        files={"file": ("huge.png", io.BytesIO(large_bytes), "image/png")},
    )
    assert res_large.status_code == 422
    assert "exceeds 5 mb" in res_large.json()["errors"][0]["detail"].lower()
