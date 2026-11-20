from uuid import UUID

import pytest

from src.api.dependencies import get_user_uow


@pytest.mark.anyio
async def test_cny_currency_crud_and_validation(client):
    # 1. Register admin and creator
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "cny_admin", "password": "Password123!"},
    )
    admin_id = reg_admin.json()["body"]["user"]["id"]

    reg_creator = await client.post(
        "/api/v1/auth/register",
        json={"login": "cny_creator", "password": "Password123!"},
    )
    creator_id = reg_creator.json()["body"]["user"]["id"]

    # Assign permissions
    uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)
    uow = uow_factory()
    async with uow:
        admin = await uow.users.get_by_id(UUID(admin_id))
        admin.global_permissions = ["catalog:manage"]
        await uow.users.update(admin)

        c = await uow.users.get_by_id(UUID(creator_id))
        c.global_permissions = ["creator:products"]
        await uow.users.update(c)
        await uow.commit()

    # Login
    res_admin = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "cny_admin", "password": "Password123!"},
    )
    admin_headers = {
        "Authorization": f"Bearer {res_admin.json()['body']['access_token']}"
    }

    res_c = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "cny_creator", "password": "Password123!"},
    )
    creator_headers = {
        "Authorization": f"Bearer {res_c.json()['body']['access_token']}"
    }

    # Admin creates category
    cat_res = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "CNY Category", "slug": "cny-category"},
    )
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["body"]["id"]

    # Validation: negative price_cny is rejected with 422
    neg_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": cat_id,
            "title": "Negative CNY Product",
            "slug": "negative-cny-product",
            "base_price": 100,
            "price_cny": -50.00,
            "is_self_worked": True,
        },
    )
    assert neg_res.status_code == 422

    # Success: create with price_cny
    create_res = await client.post(
        "/api/v1/products",
        headers=creator_headers,
        json={
            "category_id": cat_id,
            "title": "CNY Silk Shirt",
            "slug": "cny-silk-shirt",
            "base_price": 5000.00,
            "price_usd": 70.00,
            "price_eur": 65.00,
            "price_cny": 510.50,
            "is_self_worked": True,
        },
    )
    assert create_res.status_code == 201
    prod_data = create_res.json()["body"]
    assert float(prod_data["price_cny"]) == 510.50
    prod_id = prod_data["id"]

    # Update: update price_cny
    update_res = await client.patch(
        f"/api/v1/products/{prod_id}",
        headers=creator_headers,
        json={"price_cny": 550.00},
    )
    assert update_res.status_code == 200
    assert float(update_res.json()["body"]["price_cny"]) == 550.00


@pytest.mark.anyio
async def test_self_worked_requires_creator_products_permission(client):
    # 1. Register users: user_no_perm, user_drops (creator:drops), user_prod (creator:products)
    r1 = await client.post(
        "/api/v1/auth/register",
        json={"login": "user_no_perm", "password": "Password123!"},
    )
    _ = r1.json()["body"]["user"]["id"]

    r2 = await client.post(
        "/api/v1/auth/register",
        json={"login": "user_drops", "password": "Password123!"},
    )
    id2 = r2.json()["body"]["user"]["id"]

    r3 = await client.post(
        "/api/v1/auth/register",
        json={"login": "user_prod", "password": "Password123!"},
    )
    id3 = r3.json()["body"]["user"]["id"]

    # Admin to create category
    r_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "super_admin_perm", "password": "Password123!"},
    )
    admin_id = r_admin.json()["body"]["user"]["id"]

    uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)
    uow = uow_factory()
    async with uow:
        admin = await uow.users.get_by_id(UUID(admin_id))
        admin.global_permissions = ["*"]
        await uow.users.update(admin)

        u2 = await uow.users.get_by_id(UUID(id2))
        u2.global_permissions = ["creator:drops"]
        await uow.users.update(u2)

        u3 = await uow.users.get_by_id(UUID(id3))
        u3.global_permissions = ["creator:products"]
        await uow.users.update(u3)
        await uow.commit()

    # Login
    l_admin = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "super_admin_perm", "password": "Password123!"},
    )
    admin_headers = {
        "Authorization": f"Bearer {l_admin.json()['body']['access_token']}"
    }

    l_no_perm = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "user_no_perm", "password": "Password123!"},
    )
    no_perm_headers = {
        "Authorization": f"Bearer {l_no_perm.json()['body']['access_token']}"
    }

    l_drops = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "user_drops", "password": "Password123!"},
    )
    drops_headers = {
        "Authorization": f"Bearer {l_drops.json()['body']['access_token']}"
    }

    l_prod = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "user_prod", "password": "Password123!"},
    )
    prod_headers = {"Authorization": f"Bearer {l_prod.json()['body']['access_token']}"}

    # Admin creates category
    cat_res = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Self-worked Cat", "slug": "self-worked-cat"},
    )
    cat_id = cat_res.json()["body"]["id"]

    # 1. user_no_perm gets 403
    res1 = await client.post(
        "/api/v1/products",
        headers=no_perm_headers,
        json={
            "category_id": cat_id,
            "title": "Hacked Product",
            "slug": "hacked-product",
            "base_price": 100,
            "is_self_worked": True,
        },
    )
    assert res1.status_code == 403

    # 2. user_drops gets 403 with exact Russian message
    res2 = await client.post(
        "/api/v1/products",
        headers=drops_headers,
        json={
            "category_id": cat_id,
            "title": "Drops Self Worked",
            "slug": "drops-self-worked",
            "base_price": 100,
            "is_self_worked": True,
        },
    )
    assert res2.status_code == 403
    assert (
        res2.json()["errors"][0]["detail"]
        == "Для создания self-worked товаров требуется право creator:products"
    )

    # 3. user_prod with creator:products succeeds
    res3 = await client.post(
        "/api/v1/products",
        headers=prod_headers,
        json={
            "category_id": cat_id,
            "title": "Legit Self Worked",
            "slug": "legit-self-worked",
            "base_price": 100,
            "is_self_worked": True,
        },
    )
    assert res3.status_code == 201


@pytest.mark.anyio
async def test_public_user_profile_endpoint_and_creator_product_fields(client):
    # 1. Register author and admin
    r_author = await client.post(
        "/api/v1/auth/register",
        json={"login": "cool_creator", "password": "Password123!"},
    )
    author_id = r_author.json()["body"]["user"]["id"]

    r_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "profile_admin", "password": "Password123!"},
    )
    admin_id = r_admin.json()["body"]["user"]["id"]

    uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)
    uow = uow_factory()
    async with uow:
        author = await uow.users.get_by_id(UUID(author_id))
        author.global_permissions = ["creator:products"]
        author.verified_profile = True
        await uow.users.update(author)

        admin = await uow.users.get_by_id(UUID(admin_id))
        admin.global_permissions = ["*"]
        await uow.users.update(admin)
        await uow.commit()

    # Login author and admin
    l_author = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "cool_creator", "password": "Password123!"},
    )
    author_headers = {
        "Authorization": f"Bearer {l_author.json()['body']['access_token']}"
    }

    l_admin = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "profile_admin", "password": "Password123!"},
    )
    admin_headers = {
        "Authorization": f"Bearer {l_admin.json()['body']['access_token']}"
    }

    # Admin creates category
    cat_res = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Creator Street", "slug": "creator-street"},
    )
    cat_id = cat_res.json()["body"]["id"]

    # Author creates published self-worked product
    p1_res = await client.post(
        "/api/v1/products",
        headers=author_headers,
        json={
            "category_id": cat_id,
            "title": "Author Tee One",
            "slug": "author-tee-one",
            "base_price": 2500,
            "price_cny": 250,
            "is_self_worked": True,
            "is_published": True,
        },
    )
    assert p1_res.status_code == 201
    p1_id = p1_res.json()["body"]["id"]

    # Verify creator_login and creator_verified on returned product
    p1_data = p1_res.json()["body"]
    assert p1_data["creator_login"] == "cool_creator"
    assert p1_data["creator_verified"] is True
    assert float(p1_data["price_cny"]) == 250.0

    # Author creates second product (hidden=1, meaning direct link only)
    p2_res = await client.post(
        "/api/v1/products",
        headers=author_headers,
        json={
            "category_id": cat_id,
            "title": "Author Hidden Tee",
            "slug": "author-hidden-tee",
            "base_price": 3000,
            "is_self_worked": True,
            "is_published": True,
            "is_hidden": 1,
        },
    )
    assert p2_res.status_code == 201
    p2_id = p2_res.json()["body"]["id"]

    # Author creates third product (unpublished)
    p3_res = await client.post(
        "/api/v1/products",
        headers=author_headers,
        json={
            "category_id": cat_id,
            "title": "Author Unpublished Tee",
            "slug": "author-unpub-tee",
            "base_price": 4000,
            "is_self_worked": True,
            "is_published": False,
        },
    )
    assert p3_res.status_code == 201
    p3_id = p3_res.json()["body"]["id"]

    # Approve all three products via moderation
    for pid in [p1_id, p2_id, p3_id]:
        await client.post(
            f"/api/v1/moderation/products/{pid}/approve",
            headers=admin_headers,
        )

    # Public endpoint: GET /api/v1/users/{login} without auth header!
    pub_res = await client.get("/api/v1/users/cool_creator")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()["body"]

    assert pub_data["id"] == author_id
    assert pub_data["login"] == "cool_creator"
    assert pub_data["verified_profile"] is True
    assert "created_at" in pub_data

    # Only published, approved, is_hidden=0, deleted_at is None must be returned
    products = pub_data["products"]
    assert len(products) == 1
    assert products[0]["id"] == p1_id
    assert products[0]["title"] == "Author Tee One"
    assert products[0]["creator_login"] == "cool_creator"
    assert products[0]["creator_verified"] is True
    assert float(products[0]["price_cny"]) == 250.0

    # Non-existent user -> 404
    missing_res = await client.get("/api/v1/users/non_existent_author_xyz")
    assert missing_res.status_code == 404

    # Deleted author -> 404
    await client.delete("/api/v1/users/me", headers=author_headers)
    deleted_res = await client.get("/api/v1/users/cool_creator")
    assert deleted_res.status_code == 404
