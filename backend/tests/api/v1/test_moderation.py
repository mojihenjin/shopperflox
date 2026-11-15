import pytest


@pytest.mark.anyio
async def test_moderation_ban_and_instant_revocation(client):
    # 1. Register admin user and regular user
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={
            "login": "superadmin",
            "password": "Password123!",
        },
    )
    admin_id = reg_admin.json()["body"]["user"]["id"]

    reg_target = await client.post(
        "/api/v1/auth/register",
        json={
            "login": "bad_actor",
            "password": "Password123!",
        },
    )
    target_id = reg_target.json()["body"]["user"]["id"]

    # Login regular user and get access token
    target_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "bad_actor", "password": "Password123!"},
    )
    target_token = target_login.json()["body"]["access_token"]
    target_headers = {"Authorization": f"Bearer {target_token}"}

    # Verify regular user has access to /me
    me_resp = await client.get("/api/v1/users/me", headers=target_headers)
    assert me_resp.status_code == 200

    # Non-moderator tries to ban someone -> 403 Forbidden
    forbidden_ban = await client.post(
        f"/api/v1/moderation/users/{admin_id}/ban",
        headers=target_headers,
        json={"reason": "Illegal attempt"},
    )
    assert forbidden_ban.status_code == 403

    # Grant admin permissions to superadmin in DB using test UoW
    from src.api.dependencies import get_user_uow

    uow_factory = client._transport.app.dependency_overrides.get(get_user_uow)
    uow = uow_factory()
    async with uow:
        admin_user = await uow.users.get_by_login("superadmin")
        admin_user.global_permissions = ["*"]
        await uow.users.update(admin_user)
        await uow.commit()

    # Login superadmin
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "superadmin", "password": "Password123!"},
    )
    admin_token = admin_login.json()["body"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Admin bans regular user
    ban_resp = await client.post(
        f"/api/v1/moderation/users/{target_id}/ban",
        headers=admin_headers,
        json={"reason": "Terms violation: spamming"},
    )
    assert ban_resp.status_code == 200
    ban_data = ban_resp.json()["body"]
    assert ban_data["user_id"] == target_id
    assert ban_data["reason"] == "Terms violation: spamming"

    # 3. Regular user immediately attempts to use existing valid access token -> INSTANT 403!
    banned_attempt = await client.get("/api/v1/users/me", headers=target_headers)
    assert banned_attempt.status_code == 403
    assert "User is banned" in banned_attempt.json()["errors"][0]["detail"]

    # 4. Admin unbans the user
    unban_resp = await client.post(
        f"/api/v1/moderation/users/{target_id}/unban",
        headers=admin_headers,
    )
    assert unban_resp.status_code == 200

    # 5. Regular user can access /me again!
    unbanned_attempt = await client.get("/api/v1/users/me", headers=target_headers)
    assert unbanned_attempt.status_code == 200

    # 6. Admin updates user permissions
    perm_resp = await client.put(
        f"/api/v1/moderation/users/{target_id}/permissions",
        headers=admin_headers,
        json={"permissions": ["catalog:read", "orders:create"]},
    )
    assert perm_resp.status_code == 200
    assert perm_resp.json()["body"]["global_permissions"] == [
        "catalog:read",
        "orders:create",
    ]
