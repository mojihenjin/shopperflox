import pytest


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
