from uuid import UUID

import pytest
from httpx import AsyncClient

from src.api.dependencies import (
    get_catalog_uow,
    get_review_uow,
    get_task_queue,
    get_user_uow,
)
from src.infrastructure.security import JwtTokenProvider


@pytest.fixture
def auth_headers():
    provider = JwtTokenProvider()

    def _make(user_id: UUID, permissions: list[str] | None = None):
        perms = permissions or []
        token = provider.create_access_token(user_id, perms)
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.mark.anyio
async def test_admin_access_control(client: AsyncClient, auth_headers):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    # 1. Unauthenticated request to admin endpoint returns 401
    res_unauth = await client.get("/api/v1/admin/users")
    assert res_unauth.status_code == 401

    # 2. Regular user without admin permission returns 403
    reg_user = await client.post(
        "/api/v1/auth/register",
        json={"login": "regular_admin_probe", "password": "Password123!"},
    )
    user_id = UUID(reg_user.json()["body"]["user"]["id"])
    regular_headers = auth_headers(user_id, permissions=["creator:products"])

    res_forbidden = await client.get("/api/v1/admin/users", headers=regular_headers)
    assert res_forbidden.status_code == 403

    # 3. User with admin:access succeeds
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "scoped_admin_probe", "password": "Password123!"},
    )
    admin_id = UUID(reg_admin.json()["body"]["user"]["id"])
    async with user_uow:
        u = await user_uow.users.get_by_id(admin_id)
        assert u is not None
        u.global_permissions = ["admin:access"]
        await user_uow.users.update(u)
        await user_uow.commit()

    admin_headers = auth_headers(admin_id, permissions=["admin:access"])
    res_ok = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert res_ok.status_code == 200

    # 4. User with * succeeds
    reg_super = await client.post(
        "/api/v1/auth/register",
        json={"login": "super_admin_probe", "password": "Password123!"},
    )
    super_id = UUID(reg_super.json()["body"]["user"]["id"])
    async with user_uow:
        u = await user_uow.users.get_by_id(super_id)
        assert u is not None
        u.global_permissions = ["*"]
        await user_uow.users.update(u)
        await user_uow.commit()

    super_headers = auth_headers(super_id, permissions=["*"])
    res_super_ok = await client.get("/api/v1/admin/users", headers=super_headers)
    assert res_super_ok.status_code == 200


@pytest.mark.anyio
async def test_admin_user_lifecycle_ban_delete_and_reset_password(
    client: AsyncClient, auth_headers
):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    tq_factory = client._transport.app.dependency_overrides.get(get_task_queue)  # type: ignore
    user_uow = user_uow_factory()
    tq = tq_factory()

    async def create_user(
        login: str, perms: list[str] | None = None, email: str | None = None
    ):
        reg = await client.post(
            "/api/v1/auth/register",
            json={"login": login, "password": "Password123!"},
        )
        u_id = UUID(reg.json()["body"]["user"]["id"])
        async with user_uow:
            u = await user_uow.users.get_by_id(u_id)
            assert u is not None
            if perms:
                u.global_permissions = perms
            if email:
                u.email = email
            await user_uow.users.update(u)
            await user_uow.commit()
        return u_id, auth_headers(u_id, permissions=perms or [])

    admin_id, admin_headers = await create_user("super_ops_admin", ["*"])
    target_id, target_headers = await create_user(
        "target_probe_user", ["creator:products"], email="target@shopperflox.com"
    )

    # Self ban is forbidden
    self_ban_res = await client.post(
        f"/api/v1/admin/users/{admin_id}/ban",
        headers=admin_headers,
        json={"reason": "Self attack"},
    )
    assert self_ban_res.status_code == 422 or self_ban_res.status_code == 400

    # Self delete is forbidden
    self_del_res = await client.delete(
        f"/api/v1/admin/users/{admin_id}",
        headers=admin_headers,
    )
    assert self_del_res.status_code == 422 or self_del_res.status_code == 400

    # Ban target user
    ban_res = await client.post(
        f"/api/v1/admin/users/{target_id}/ban",
        headers=admin_headers,
        json={"reason": "Spam and abuse"},
    )
    assert ban_res.status_code == 200
    assert ban_res.json()["body"]["reason"] == "Spam and abuse"

    # Banned user access returns 403 Forbidden with ban reason
    banned_access = await client.get("/api/v1/users/me", headers=target_headers)
    assert banned_access.status_code == 403
    assert "Spam and abuse" in str(banned_access.json())

    # Verify banned user cannot log in (403 Forbidden)
    banned_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "target_probe_user", "password": "Password123!"},
    )
    assert banned_login.status_code == 403
    assert "Spam and abuse" in str(banned_login.json())

    # Filter banned users in admin
    list_banned = await client.get(
        "/api/v1/admin/users?status=banned", headers=admin_headers
    )
    assert list_banned.status_code == 200
    banned_users = list_banned.json()["body"]
    assert any(u["id"] == str(target_id) for u in banned_users)

    # Unban target user
    unban_res = await client.post(
        f"/api/v1/admin/users/{target_id}/unban",
        headers=admin_headers,
    )
    assert unban_res.status_code == 200

    # User can log in again
    unbanned_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "target_probe_user", "password": "Password123!"},
    )
    assert unbanned_login.status_code == 200

    # Update user profile verification and permissions
    patch_res = await client.patch(
        f"/api/v1/admin/users/{target_id}",
        headers=admin_headers,
        json={"verified_profile": True, "global_permissions": ["catalog:manage"]},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["body"]["verified_profile"] is True
    assert "catalog:manage" in patch_res.json()["body"]["global_permissions"]

    # Reset password
    initial_queue_len = len(getattr(tq, "sent_emails", []))
    reset_res = await client.post(
        f"/api/v1/admin/users/{target_id}/reset-password",
        headers=admin_headers,
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["body"]["success"] is True

    # Email enqueued with new password
    sent_emails = getattr(tq, "sent_emails", [])
    assert len(sent_emails) > initial_queue_len
    last_email = sent_emails[-1]
    assert last_email[0] == "target@shopperflox.com"
    temp_password = (
        last_email[2].split("Your temporary password is: ")[1].split("\n")[0]
    )

    # Old password fails
    old_pw_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "target_probe_user", "password": "Password123!"},
    )
    assert old_pw_login.status_code == 401

    # Session token issued prior to password reset is revoked in blacklist (401 Unauthorized)
    revoked_token_access = await client.get("/api/v1/users/me", headers=target_headers)
    assert revoked_token_access.status_code == 401

    # Soft delete user
    del_res = await client.delete(
        f"/api/v1/admin/users/{target_id}",
        headers=admin_headers,
    )
    assert del_res.status_code == 200

    # Filter deleted users in admin
    list_deleted = await client.get(
        "/api/v1/admin/users?status=deleted", headers=admin_headers
    )
    assert list_deleted.status_code == 200
    assert any(u["id"] == str(target_id) for u in list_deleted.json()["body"])

    # Deleted user cannot log in (403 Forbidden) even with correct temporary password
    deleted_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "target_probe_user", "password": temp_password},
    )
    assert deleted_login.status_code == 403
    assert "deleted" in str(deleted_login.json()).lower()

    # Deleted user token access fails with 403 Forbidden
    fresh_deleted_headers = auth_headers(target_id)
    deleted_access = await client.get("/api/v1/users/me", headers=fresh_deleted_headers)
    assert deleted_access.status_code == 403


@pytest.mark.anyio
async def test_admin_brands_workflow_and_hide_products(
    client: AsyncClient, auth_headers
):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    catalog_uow_factory = client._transport.app.dependency_overrides.get(
        get_catalog_uow
    )  # type: ignore
    user_uow = user_uow_factory()
    catalog_uow = catalog_uow_factory()

    # Register admin
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "brand_admin_user", "password": "Password123!"},
    )
    admin_id = UUID(reg_admin.json()["body"]["user"]["id"])
    async with user_uow:
        u = await user_uow.users.get_by_id(admin_id)
        assert u is not None
        u.global_permissions = ["*"]
        await user_uow.users.update(u)
        await user_uow.commit()

    admin_headers = auth_headers(admin_id, permissions=["*"])

    # Create category
    cat_res = await client.post(
        "/api/v1/admin/categories",
        headers=admin_headers,
        json={"name": "Outerwear", "sort_order": 1},
    )
    assert cat_res.status_code == 201
    category_id = cat_res.json()["body"]["id"]

    # Create brand
    brand_res = await client.post(
        "/api/v1/brands",
        headers=admin_headers,
        json={"name": "CyberStreet", "his_url": "https://cyberstreet.io"},
    )
    assert brand_res.status_code == 201
    brand_id = brand_res.json()["body"]["id"]

    # Create product under brand
    prod_res = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "title": "Cyber Windbreaker",
            "slug": "cyber-windbreaker",
            "category_id": category_id,
            "brand_id": brand_id,
            "base_price": "299.99",
            "variants": [
                {
                    "size": "L",
                    "color_name": "NEON",
                    "stock_quantity": 10,
                }
            ],
        },
    )
    assert prod_res.status_code == 201
    product_id = prod_res.json()["body"]["id"]

    # List brands via admin endpoint
    list_res = await client.get(
        "/api/v1/admin/brands?search=CyberStreet", headers=admin_headers
    )
    assert list_res.status_code == 200
    brands_data = list_res.json()["body"]
    assert len(brands_data) >= 1
    found_brand = next(b for b in brands_data if b["id"] == brand_id)
    assert found_brand["name"] == "CyberStreet"
    assert len(found_brand["members"]) >= 1

    # Hide all products under brand
    hide_res = await client.post(
        f"/api/v1/admin/brands/{brand_id}/hide-all-products",
        headers=admin_headers,
    )
    assert hide_res.status_code == 200
    assert hide_res.json()["body"]["updated_count"] >= 1

    # Verify product is now hidden (is_hidden == 2)
    async with catalog_uow:
        p = await catalog_uow.products.get_by_id(
            UUID(product_id), include_unpublished=True
        )
        assert p is not None
        assert p.is_hidden == 2

    # Remoderate brand
    remod_res = await client.post(
        f"/api/v1/admin/brands/{brand_id}/remoderate",
        headers=admin_headers,
    )
    assert remod_res.status_code == 200
    assert remod_res.json()["body"]["moderation_status"] == "pending"


@pytest.mark.anyio
async def test_admin_categories_and_conflict_handling(
    client: AsyncClient, auth_headers
):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "category_admin_boss", "password": "Password123!"},
    )
    admin_id = UUID(reg_admin.json()["body"]["user"]["id"])
    async with user_uow:
        u = await user_uow.users.get_by_id(admin_id)
        assert u is not None
        u.global_permissions = ["*"]
        await user_uow.users.update(u)
        await user_uow.commit()

    admin_headers = auth_headers(admin_id, permissions=["*"])

    # 1. Create parent category
    cat1_res = await client.post(
        "/api/v1/admin/categories",
        headers=admin_headers,
        json={"name": "Techwear Admin", "sort_order": 5},
    )
    assert cat1_res.status_code == 201
    cat1_id = cat1_res.json()["body"]["id"]

    # 2. Create child category
    cat2_res = await client.post(
        "/api/v1/admin/categories",
        headers=admin_headers,
        json={"name": "Pants Tech", "parent_id": cat1_id, "sort_order": 10},
    )
    assert cat2_res.status_code == 201
    cat2_id = cat2_res.json()["body"]["id"]

    # 3. List categories
    list_cat = await client.get(
        "/api/v1/admin/categories?search=Techwear", headers=admin_headers
    )
    assert list_cat.status_code == 200
    assert any(c["id"] == cat1_id for c in list_cat.json()["body"])

    # 4. Update category
    patch_cat = await client.patch(
        f"/api/v1/admin/categories/{cat2_id}",
        headers=admin_headers,
        json={"name": "Tactical Pants", "sort_order": 2},
    )
    assert patch_cat.status_code == 200
    assert patch_cat.json()["body"]["name"] == "Tactical Pants"

    # 5. Create product linked to cat2
    prod_res = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "title": "Tactical Cargo Pants",
            "slug": "tactical-cargo-pants",
            "category_id": cat2_id,
            "base_price": "140.00",
            "variants": [
                {
                    "size": "M",
                    "color_name": "BLACK",
                    "stock_quantity": 5,
                }
            ],
        },
    )
    assert prod_res.status_code == 201

    # 6. Deleting category with associated products returns 409 Conflict
    del_conflict = await client.delete(
        f"/api/v1/admin/categories/{cat2_id}",
        headers=admin_headers,
    )
    assert del_conflict.status_code == 409

    # 7. Delete parent category with 0 products succeeds
    del_ok = await client.delete(
        f"/api/v1/admin/categories/{cat1_id}",
        headers=admin_headers,
    )
    assert del_ok.status_code == 200
    assert del_ok.json()["body"]["success"] is True


@pytest.mark.anyio
async def test_admin_products_and_reviews_lifecycle(client: AsyncClient, auth_headers):
    user_uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)  # type: ignore
    user_uow = user_uow_factory()

    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"login": "prod_review_admin", "password": "Password123!"},
    )
    admin_id = UUID(reg_admin.json()["body"]["user"]["id"])
    async with user_uow:
        u = await user_uow.users.get_by_id(admin_id)
        assert u is not None
        u.global_permissions = ["*"]
        await user_uow.users.update(u)
        await user_uow.commit()

    admin_headers = auth_headers(admin_id, permissions=["*"])

    # Create category & product
    cat_res = await client.post(
        "/api/v1/admin/categories",
        headers=admin_headers,
        json={"name": "Accessories Special", "sort_order": 1},
    )
    category_id = cat_res.json()["body"]["id"]

    prod_res = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "title": "Tactical Belt Matrix",
            "slug": "tactical-belt-matrix",
            "category_id": category_id,
            "base_price": "55.00",
            "variants": [
                {
                    "size": "ONE SIZE",
                    "color_name": "STEEL",
                    "stock_quantity": 20,
                }
            ],
        },
    )
    product_id = prod_res.json()["body"]["id"]

    # Remoderate product via admin
    remod_prod = await client.post(
        f"/api/v1/admin/products/{product_id}/remoderate",
        headers=admin_headers,
    )
    assert remod_prod.status_code == 200
    assert remod_prod.json()["body"]["moderation_status"] == "pending"

    # List products in admin
    list_prods = await client.get(
        "/api/v1/admin/products?search=Belt", headers=admin_headers
    )
    assert list_prods.status_code == 200
    assert any(p["id"] == product_id for p in list_prods.json()["body"])

    # Create review for product directly in DB
    from src.domain.models import ReviewDomain

    review_uow_factory = client._transport.app.dependency_overrides.get(get_review_uow)
    review_uow = review_uow_factory()
    review = ReviewDomain(
        user_id=admin_id,
        product_id=UUID(product_id),
        rating=5,
        comment="Outstanding tactical belt quality!",
        created_by=admin_id,
    )
    async with review_uow:
        await review_uow.reviews.add(review)
        await review_uow.commit()
    review_id = str(review.id)

    # List reviews in admin with filtering and sorting
    list_revs = await client.get(
        "/api/v1/admin/reviews?rating=5&search=Outstanding",
        headers=admin_headers,
    )
    assert list_revs.status_code == 200
    revs_data = list_revs.json()["body"]
    assert len(revs_data) >= 1
    found_rev = next(r for r in revs_data if r["id"] == review_id)
    assert found_rev["rating"] == 5
    assert found_rev["user_login"] == "prod_review_admin"
    assert found_rev["product_title"] == "Tactical Belt Matrix"

    # Delete review as admin
    del_rev = await client.delete(
        f"/api/v1/admin/reviews/{review_id}",
        headers=admin_headers,
    )
    assert del_rev.status_code == 200
    assert del_rev.json()["body"]["success"] is True

    # Verify review no longer in list
    list_after = await client.get(
        f"/api/v1/products/{product_id}/reviews",
    )
    assert not any(r["id"] == review_id for r in list_after.json()["body"])
