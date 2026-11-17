from uuid import UUID

import pytest

from src.api.dependencies import get_user_uow


@pytest.mark.anyio
async def test_product_image_reordering(client):
    # 1. Register admin, creator, stranger
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "reorder_admin", "password": "Password123!"},
    )
    admin_id = reg_admin.json()["body"]["user"]["id"]

    reg_creator = await client.post(
        "/api/v1/auth/register",
        json={"login": "reorder_creator", "password": "Password123!"},
    )
    creator_id = reg_creator.json()["body"]["user"]["id"]

    reg_stranger = await client.post(
        "/api/v1/auth/register",
        json={"login": "reorder_stranger", "password": "Password123!"},
    )
    _ = reg_stranger.json()["body"]["user"]["id"]

    # Assign permissions
    uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)
    uow = uow_factory()
    async with uow:
        admin = await uow.users.get_by_id(UUID(admin_id))
        admin.global_permissions = ["catalog:manage", "mod:approve_manager"]
        await uow.users.update(admin)

        c = await uow.users.get_by_id(UUID(creator_id))
        c.global_permissions = ["creator:products"]
        await uow.users.update(c)
        await uow.commit()

    # Logins
    res_admin = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "reorder_admin", "password": "Password123!"},
    )
    admin_headers = {
        "Authorization": f"Bearer {res_admin.json()['body']['access_token']}"
    }

    res_c = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "reorder_creator", "password": "Password123!"},
    )
    creator_headers = {
        "Authorization": f"Bearer {res_c.json()['body']['access_token']}"
    }

    res_s = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "reorder_stranger", "password": "Password123!"},
    )
    stranger_headers = {
        "Authorization": f"Bearer {res_s.json()['body']['access_token']}"
    }

    # Admin creates category
    cat_res = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Reorder Category", "slug": "reorder-category"},
    )
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["body"]["id"]

    # Creator creates self-worked product
    prod_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": cat_id,
            "title": "Reorder Product",
            "slug": "reorder-product",
            "is_self_worked": True,
            "base_price": "100.00",
            "variants": [
                {
                    "sku": "REORDER-1",
                    "size": "L",
                    "color_name": "Black",
                    "stock_quantity": 10,
                }
            ],
        },
    )
    assert prod_res.status_code == 201
    product_id = prod_res.json()["body"]["id"]

    # Add 3 images
    img1_res = await client.post(
        f"/api/v1/products/{product_id}/images",
        headers=creator_headers,
        json={
            "url": "https://example.com/img1.png",
            "sort_order": 0,
            "color": "black",
            "is_main": True,
        },
    )
    assert img1_res.status_code == 201
    img1_id = img1_res.json()["body"]["id"]

    img2_res = await client.post(
        f"/api/v1/products/{product_id}/images",
        headers=creator_headers,
        json={
            "url": "https://example.com/img2.png",
            "sort_order": 1,
            "color": "white",
            "is_main": False,
        },
    )
    assert img2_res.status_code == 201
    img2_id = img2_res.json()["body"]["id"]

    img3_res = await client.post(
        f"/api/v1/products/{product_id}/images",
        headers=creator_headers,
        json={
            "url": "https://example.com/img3.png",
            "sort_order": 2,
            "color": "blue",
            "is_main": False,
        },
    )
    assert img3_res.status_code == 201
    img3_id = img3_res.json()["body"]["id"]

    # 1. Stranger attempts reordering -> 403 Forbidden
    reorder_payload = [
        {"image_id": img3_id, "sort_order": 0, "color": "navy"},
        {"image_id": img1_id, "sort_order": 1},
        {"image_id": img2_id, "sort_order": 2},
    ]
    stranger_res = await client.patch(
        f"/api/v1/products/{product_id}/images/reorder",
        headers=stranger_headers,
        json=reorder_payload,
    )
    assert stranger_res.status_code == 403

    # 2. Creator reorders successfully
    creator_reorder = await client.patch(
        f"/api/v1/products/{product_id}/images/reorder",
        headers=creator_headers,
        json=reorder_payload,
    )
    assert creator_reorder.status_code == 200
    images = creator_reorder.json()["body"]
    assert len(images) == 3

    # Verify new ordering and is_main status
    img_by_id = {img["id"]: img for img in images}
    assert img_by_id[img3_id]["sort_order"] == 0
    assert img_by_id[img3_id]["is_main"] is True
    assert img_by_id[img3_id]["color"] == "navy"

    assert img_by_id[img1_id]["sort_order"] == 1
    assert img_by_id[img1_id]["is_main"] is False
    assert img_by_id[img1_id]["color"] == "black"  # Color preserved because omitted

    assert img_by_id[img2_id]["sort_order"] == 2
    assert img_by_id[img2_id]["is_main"] is False
    assert img_by_id[img2_id]["color"] == "white"

    # 3. Test wrapped object format {"items": [...]}
    wrapped_payload = {
        "items": [
            {"image_id": img2_id, "sort_order": 0, "color": "pearl"},
            {"image_id": img3_id, "sort_order": 1},
            {"image_id": img1_id, "sort_order": 2},
        ]
    }
    admin_reorder = await client.patch(
        f"/api/v1/products/{product_id}/images/reorder",
        headers=admin_headers,
        json=wrapped_payload,
    )
    assert admin_reorder.status_code == 200
    images_admin = admin_reorder.json()["body"]
    img_admin_map = {img["id"]: img for img in images_admin}
    assert img_admin_map[img2_id]["sort_order"] == 0
    assert img_admin_map[img2_id]["is_main"] is True
    assert img_admin_map[img2_id]["color"] == "pearl"
    assert img_admin_map[img3_id]["is_main"] is False
    assert img_admin_map[img1_id]["is_main"] is False

    # 4. Error cases: duplicate image_id -> 422 Unprocessable Entity
    dup_res = await client.patch(
        f"/api/v1/products/{product_id}/images/reorder",
        headers=creator_headers,
        json=[
            {"image_id": img1_id, "sort_order": 0},
            {"image_id": img1_id, "sort_order": 1},
        ],
    )
    assert dup_res.status_code == 422

    # 5. Non-existent product -> 404 Not Found
    fake_prod_id = "00000000-0000-0000-0000-000000000000"
    missing_prod = await client.patch(
        f"/api/v1/products/{fake_prod_id}/images/reorder",
        headers=admin_headers,
        json=[{"image_id": img1_id, "sort_order": 0}],
    )
    assert missing_prod.status_code == 404

    # 6. Foreign image_id -> 404 Not Found
    fake_img_id = "00000000-0000-0000-0000-000000000001"
    foreign_img = await client.patch(
        f"/api/v1/products/{product_id}/images/reorder",
        headers=admin_headers,
        json=[{"image_id": fake_img_id, "sort_order": 0}],
    )
    assert foreign_img.status_code == 404
