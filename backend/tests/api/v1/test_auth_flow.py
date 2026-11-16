from uuid import UUID

import pytest

from src.api.dependencies import get_user_uow
from src.infrastructure.security import JwtTokenProvider


@pytest.mark.anyio
async def test_full_auth_flow(client, test_task_queue):
    # 1. Register a new user with email
    register_payload = {
        "login": "alice_flow",
        "password": "Password123!",
        "email": "alice_flow@example.com",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_resp.status_code == 200
    reg_init = reg_resp.json()["body"]
    assert reg_init["requires_verification"] is True
    token = reg_init["verification_token"]
    assert token

    # Get code from queue and confirm verification
    code = test_task_queue.sent_emails[-1][2]
    confirm_resp = await client.post(
        "/api/v1/auth/verification-code",
        json={"verification_token": token, "code": code},
    )
    assert confirm_resp.status_code == 201
    reg_data = confirm_resp.json()
    assert reg_data["body"]["login"] == "alice_flow"
    assert reg_data["body"]["email"] == "alice_flow@example.com"
    assert reg_data["body"]["verified_email"] is True
    # Categorically no password_hash in response
    assert "password_hash" not in reg_data["body"]
    assert "password" not in reg_data["body"]

    # 2. Login with login
    login_payload = {
        "identifier": "alice_flow",
        "password": "Password123!",
    }
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["status_code"] == 200
    access_token = login_data["body"]["access_token"]
    refresh_token = login_data["body"]["refresh_token"]
    assert access_token
    assert refresh_token
    assert login_data["body"]["token_type"] == "bearer"

    # Verify access_token payload claims
    jwt_provider = JwtTokenProvider()
    token_claims = jwt_provider.decode_token(access_token)
    assert token_claims["login"] == "alice_flow"
    assert token_claims["global_permissions"] == []
    assert token_claims["verified_profile"] is False
    assert token_claims["verified_email"] is True

    # Also login with case-insensitive login
    login_case_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "ALICE_FLOW", "password": "Password123!"},
    )
    assert login_case_resp.status_code == 200

    # Also login with email
    login_email_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "alice_flow@example.com", "password": "Password123!"},
    )
    assert login_email_resp.status_code == 200

    # 3. Request /api/v1/users/me with valid access_token
    headers = {"Authorization": f"Bearer {access_token}"}
    me_resp = await client.get("/api/v1/users/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["status_code"] == 200
    assert me_data["body"]["user"]["login"] == "alice_flow"
    assert "password_hash" not in me_data["body"]["user"]

    # 4. Attempt to pass refresh_token in Authorization: Bearer (expect 401)
    refresh_as_bearer_headers = {"Authorization": f"Bearer {refresh_token}"}
    unauthorized_resp = await client.get(
        "/api/v1/users/me", headers=refresh_as_bearer_headers
    )
    assert unauthorized_resp.status_code == 401
    unauthorized_data = unauthorized_resp.json()
    assert unauthorized_data["status_code"] == 401
    assert any(
        "expected 'access'" in err["detail"] or "Invalid" in err["detail"]
        for err in unauthorized_data["errors"]
    )

    # Attempt to access /api/v1/users/me with no header (expect 401)
    no_auth_resp = await client.get("/api/v1/users/me")
    assert no_auth_resp.status_code == 401

    # 5. Refresh tokens through /api/v1/auth/refresh
    refresh_req = {"refresh_token": refresh_token}
    refresh_resp = await client.post("/api/v1/auth/refresh", json=refresh_req)
    assert refresh_resp.status_code == 200
    refreshed_data = refresh_resp.json()
    new_access_token = refreshed_data["body"]["access_token"]
    new_refresh_token = refreshed_data["body"]["refresh_token"]
    assert new_access_token
    assert new_refresh_token

    # Verify refreshed access_token payload claims
    refreshed_claims = jwt_provider.decode_token(new_access_token)
    assert refreshed_claims["login"] == "alice_flow"
    assert refreshed_claims["global_permissions"] == []
    assert refreshed_claims["verified_profile"] is False
    assert refreshed_claims["verified_email"] is True

    # 6. Verify newly refreshed access token works on /users/me
    new_headers = {"Authorization": f"Bearer {new_access_token}"}
    new_me_resp = await client.get("/api/v1/users/me", headers=new_headers)
    assert new_me_resp.status_code == 200
    assert new_me_resp.json()["body"]["user"]["login"] == "alice_flow"

    # 7. Attempt to pass access_token as refresh_token into /auth/refresh (expect 401)
    invalid_refresh_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": new_access_token}
    )
    assert invalid_refresh_resp.status_code == 401

    # 8. Attempt to REUSE the old refresh_token (SEC-01 blacklist check, expect 401)
    reuse_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert reuse_resp.status_code == 401
    assert "revoked" in reuse_resp.json()["errors"][0]["detail"].lower()

    # 9. Logout using new_refresh_token and active access_token header
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_refresh_token},
        headers=new_headers,
    )
    assert logout_resp.status_code == 200

    # 10. Attempt to use new_refresh_token after logout (expect 401)
    post_logout_refresh = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": new_refresh_token}
    )
    assert post_logout_refresh.status_code == 401
    assert "revoked" in post_logout_refresh.json()["errors"][0]["detail"].lower()

    # 11. Attempt to use logged-out access_token immediately (expect 401 revoked)
    post_logout_me = await client.get("/api/v1/users/me", headers=new_headers)
    assert post_logout_me.status_code == 401
    assert "revoked" in post_logout_me.json()["errors"][0]["detail"].lower()


@pytest.mark.anyio
async def test_access_token_claims_and_permission_update_on_refresh(
    client, test_task_queue
):
    token_provider = JwtTokenProvider()

    # 1. Register and verify user
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "login": "bob_claims",
            "password": "Password123!",
            "email": "bob_claims@example.com",
        },
    )
    token = reg_resp.json()["body"]["verification_token"]
    code = test_task_queue.sent_emails[-1][2]
    await client.post(
        "/api/v1/auth/verification-code",
        json={"verification_token": token, "code": code},
    )

    # 2. Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "bob_claims", "password": "Password123!"},
    )
    body = login_resp.json()["body"]
    access_token = body["access_token"]
    refresh_token = body["refresh_token"]

    claims = token_provider.decode_token(access_token)
    assert claims["login"] == "bob_claims"
    assert claims["global_permissions"] == []
    assert claims["verified_profile"] is False
    assert claims["verified_email"] is True

    # 3. Update permissions and verified_profile in DB
    user_id = UUID(claims["sub"])
    uow_fn = client._transport.app.dependency_overrides[get_user_uow]
    uow = uow_fn()
    async with uow:
        user = await uow.users.get_by_id(user_id)
        assert user is not None
        user.global_permissions = ["catalog:manage", "creator:brand"]
        user.verified_profile = True
        await uow.users.update(user)
        await uow.commit()

    # 4. Refresh tokens
    ref_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_resp.status_code == 200
    new_access_token = ref_resp.json()["body"]["access_token"]

    # 5. Verify updated claims in new access token
    new_claims = token_provider.decode_token(new_access_token)
    assert new_claims["login"] == "bob_claims"
    assert new_claims["global_permissions"] == ["catalog:manage", "creator:brand"]
    assert new_claims["verified_profile"] is True
    assert new_claims["verified_email"] is True

    # 6. Verify permission works with new access token
    cat_resp = await client.post(
        "/api/v1/categories",
        headers={"Authorization": f"Bearer {new_access_token}"},
        json={"name": "Bob Category", "slug": "bob-category"},
    )
    assert cat_resp.status_code == 201
