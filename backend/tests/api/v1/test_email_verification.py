import pytest

pytestmark = pytest.mark.anyio


async def test_email_verification_branches_and_burning(
    client, test_task_queue, test_email_store
):
    # 1. Регистрация без email -> сразу 201, verified_email=False
    reg_no_email = await client.post(
        "/api/v1/auth/register",
        json={"login": "no_email_user", "password": "Password123!"},
    )
    assert reg_no_email.status_code == 201
    no_email_data = reg_no_email.json()["body"]
    assert no_email_data["requires_verification"] is False
    assert no_email_data["verification_token"] is None
    assert no_email_data["user"]["login"] == "no_email_user"
    assert no_email_data["user"]["email"] is None
    assert no_email_data["user"]["verified_email"] is False

    # 2. Регистрация с email -> 200 + verification_token (пользователя в БД нет)
    reg_with_email = await client.post(
        "/api/v1/auth/register",
        json={
            "login": "with_email_user",
            "password": "Password123!",
            "email": "with_email@example.com",
        },
    )
    assert reg_with_email.status_code == 200
    email_reg_data = reg_with_email.json()["body"]
    assert email_reg_data["requires_verification"] is True
    verification_token = email_reg_data["verification_token"]
    assert verification_token
    assert email_reg_data["user"] is None

    # Проверяем, что в БД пользователя ещё нет (логин не сработает)
    login_attempt = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "with_email_user", "password": "Password123!"},
    )
    assert login_attempt.status_code == 401

    # Письмо с кодом поставлено в очередь
    assert len(test_task_queue.sent_emails) == 1
    to_email, subject, sent_code = test_task_queue.sent_emails[0]
    assert to_email == "with_email@example.com"
    assert "Код подтверждения" in subject
    assert "-" in sent_code and len(sent_code) == 7

    # Повторная попытка зарегистрироваться с тем же email сразу бьётся о кулдаун
    cooldown_res = await client.post(
        "/api/v1/auth/register",
        json={
            "login": "another_login",
            "password": "Password123!",
            "email": "with_email@example.com",
        },
    )
    assert cooldown_res.status_code == 422
    assert "cooldown" in cooldown_res.json()["errors"][0]["detail"].lower()

    # 4. Сгорание verification_token после 5 неверных попыток ввода кода
    for _ in range(4):
        wrong_res = await client.post(
            "/api/v1/auth/verification-code",
            json={"verification_token": verification_token, "code": "000-000"},
        )
        assert wrong_res.status_code == 401

    # 5-я неудачная попытка сжигает токен сессии
    fifth_res = await client.post(
        "/api/v1/auth/verification-code",
        json={"verification_token": verification_token, "code": "000-000"},
    )
    assert fifth_res.status_code == 401

    # 6-я попытка даже с правильным кодом возвращает ошибку истёкшей/недействительной сессии
    burned_res = await client.post(
        "/api/v1/auth/verification-code",
        json={"verification_token": verification_token, "code": sent_code},
    )
    assert burned_res.status_code == 422
    assert "expired or invalid" in burned_res.json()["errors"][0]["detail"].lower()

    # Успешная регистрация с подтверждением кода
    test_email_store.cooldowns.clear()
    reg_fresh = await client.post(
        "/api/v1/auth/register",
        json={
            "login": "verified_guy",
            "password": "Password123!",
            "email": "verified@example.com",
        },
    )
    assert reg_fresh.status_code == 200
    fresh_token = reg_fresh.json()["body"]["verification_token"]
    _, _, fresh_code = test_task_queue.sent_emails[-1]

    # Подтверждаем код без дефиса (нормализация формата "XXXXXX")
    confirm_res = await client.post(
        "/api/v1/auth/verification-code",
        json={
            "verification_token": fresh_token,
            "code": fresh_code.replace("-", ""),
        },
    )
    assert confirm_res.status_code == 201
    user_data = confirm_res.json()["body"]
    assert user_data["login"] == "verified_guy"
    assert user_data["email"] == "verified@example.com"
    assert user_data["verified_email"] is True

    # Теперь в БД пользователь есть и может авторизоваться
    login_ok = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "verified_guy", "password": "Password123!"},
    )
    assert login_ok.status_code == 200


async def test_bind_email_flow_for_user_without_email(
    client, test_task_queue, test_email_store
):
    # 3. Привязка email для юзера без почты
    # Регистрируем пользователя без почты
    reg = await client.post(
        "/api/v1/auth/register",
        json={"login": "user_bind", "password": "Password123!"},
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "user_bind", "password": "Password123!"},
    )
    token = login.json()["body"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Авторизованный запрос кода привязки
    send_res = await client.post(
        "/api/v1/auth/email/send-code",
        headers=headers,
        json={"email": "bind_me@example.com"},
    )
    assert send_res.status_code == 200
    bind_token = send_res.json()["body"]["verification_token"]
    _, _, bind_code = test_task_queue.sent_emails[-1]

    # Подтверждаем код через единую ручку POST /api/v1/auth/verification-code
    confirm_bind = await client.post(
        "/api/v1/auth/verification-code",
        json={"verification_token": bind_token, "code": bind_code},
    )
    assert confirm_bind.status_code == 200
    assert confirm_bind.json()["body"]["email"] == "bind_me@example.com"
    assert confirm_bind.json()["body"]["verified_email"] is True

    # Профиль пользователя обновился
    me_res = await client.get("/api/v1/users/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["body"]["user"]["email"] == "bind_me@example.com"
    assert me_res.json()["body"]["user"]["verified_email"] is True
