import pytest

pytestmark = pytest.mark.anyio


async def test_email_verification_full_flow(client, test_task_queue, test_email_store):
    # 1. Register a user with email
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "login": "verify_user",
            "password": "Password123!",
            "email": "verify_user@example.com",
        },
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "verify_user", "password": "Password123!"},
    )
    token = login.json()["body"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Request verification code
    send_res = await client.post("/api/v1/auth/email/send-code", headers=headers)
    assert send_res.status_code == 200

    # Task was enqueued
    assert len(test_task_queue.sent_emails) == 1
    to_email, subject, sent_code = test_task_queue.sent_emails[0]
    assert to_email == "verify_user@example.com"
    assert "Код подтверждения" in subject
    assert "-" in sent_code and len(sent_code) == 7

    # 3. Cooldown check - immediate repeat request must fail
    repeat_res = await client.post("/api/v1/auth/email/send-code", headers=headers)
    assert repeat_res.status_code == 422
    assert "cooldown" in repeat_res.json()["errors"][0]["detail"].lower()

    # 4. Wrong code attempts - burn after 5 attempts
    for attempt in range(4):
        wrong_res = await client.post(
            "/api/v1/auth/email/verify",
            headers=headers,
            json={"code": "000-000"},
        )
        assert wrong_res.status_code == 401

    # 5th failed attempt deletes the OTP code
    fifth_res = await client.post(
        "/api/v1/auth/email/verify",
        headers=headers,
        json={"code": "000-000"},
    )
    assert fifth_res.status_code == 401

    # 6th attempt fails with expired/not requested because code burned
    burned_res = await client.post(
        "/api/v1/auth/email/verify",
        headers=headers,
        json={"code": sent_code},
    )
    assert burned_res.status_code == 422
    assert "expired" in burned_res.json()["errors"][0]["detail"].lower()

    # 5. Success flow with normalized code
    # Clear cooldown manually for test
    test_email_store.cooldowns.clear()

    send_res_2 = await client.post("/api/v1/auth/email/send-code", headers=headers)
    assert send_res_2.status_code == 200
    _, _, fresh_code = test_task_queue.sent_emails[-1]

    # Send without hyphen (e.g. "123456")
    code_raw = fresh_code.replace("-", "")
    verify_res = await client.post(
        "/api/v1/auth/email/verify",
        headers=headers,
        json={"code": code_raw},
    )
    assert verify_res.status_code == 200

    # Verify user profile now has verified_email = True
    me_res = await client.get("/api/v1/users/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["body"]["user"]["verified_email"] is True

    # Sending code again must fail with "Email already verified"
    test_email_store.cooldowns.clear()
    already_res = await client.post("/api/v1/auth/email/send-code", headers=headers)
    assert already_res.status_code == 422
    assert "already verified" in already_res.json()["errors"][0]["detail"].lower()
