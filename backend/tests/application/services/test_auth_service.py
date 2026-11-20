from datetime import UTC, datetime, timedelta

import pytest
from uuid6 import uuid7

from src.application.services import AuthService
from src.domain.exceptions import (
    AuthenticationError,
    DomainValidationError,
    EntityAlreadyExistsError,
    PermissionDeniedError,
)
from src.domain.models import UserBanDomain, UserDomain


class MockVerificationStore:
    def __init__(self):
        self.sessions = {}
        self.cooldowns = set()
        self.user_cooldowns = set()

    async def save_session(self, token, payload, ttl_seconds=600):
        self.sessions[token] = dict(payload)

    async def get_session(self, token):
        s = self.sessions.get(token)
        return dict(s) if s else None

    async def increment_attempts(self, token):
        s = self.sessions.get(token)
        if not s:
            return -1
        attempts = int(s.get("attempts", 0)) + 1
        s["attempts"] = attempts
        if attempts >= 5:
            self.sessions.pop(token, None)
            return 5
        return attempts

    async def delete_session(self, token):
        self.sessions.pop(token, None)

    async def check_and_set_cooldown(self, email, ttl_seconds=60):
        clean = email.strip().lower()
        if clean in self.cooldowns:
            return False
        self.cooldowns.add(clean)
        return True

    async def check_and_set_user_cooldown(self, user_id, ttl_seconds=60):
        uid = str(user_id)
        if uid in self.user_cooldowns:
            return False
        self.user_cooldowns.add(uid)
        return True


class MockTaskQueue:
    def __init__(self):
        self.sent = []

    async def enqueue_email(self, to_email, subject, body_text):
        self.sent.append((to_email, subject, body_text))


@pytest.mark.anyio
async def test_register_success(uow, hasher, token_provider):
    service = AuthService(uow=uow, hasher=hasher, token_provider=token_provider)

    res = await service.register(
        login="  Alice  ",
        password="secretpassword",
    )

    assert res.requires_verification is False
    assert res.verification_token is None
    user = res.user
    assert user is not None
    assert user.login == "Alice"
    assert user.email is None
    assert user.password_hash == "hashed_secretpassword"
    assert uow.committed is True

    # Personal profile must exist
    personal = await uow.personal.get_by_user_id(user.id)
    assert personal is not None
    assert personal.id == user.id


@pytest.mark.anyio
async def test_register_empty_login_fails(uow, hasher, token_provider):
    service = AuthService(uow=uow, hasher=hasher, token_provider=token_provider)

    with pytest.raises(DomainValidationError, match="Login cannot be empty"):
        await service.register(login="   ", password="password123")


@pytest.mark.anyio
async def test_register_duplicate_login_fails(uow, hasher, token_provider):
    service = AuthService(uow=uow, hasher=hasher, token_provider=token_provider)

    await service.register(login="bob", password="password123")

    with pytest.raises(EntityAlreadyExistsError, match="already exists"):
        await service.register(login="bob", password="different_password")

    # Case-insensitive duplicate check
    with pytest.raises(EntityAlreadyExistsError, match="already exists"):
        await service.register(login="BOB", password="different_password")


@pytest.mark.anyio
async def test_register_duplicate_email_fails(uow, hasher, token_provider):
    store = MockVerificationStore()
    queue = MockTaskQueue()
    service = AuthService(
        uow=uow,
        hasher=hasher,
        token_provider=token_provider,
        verification_store=store,
        task_queue=queue,
    )

    res = await service.register(
        login="charlie1", password="password123", email="charlie@test.com"
    )
    code = queue.sent[0][2]
    await service.confirm_verification_code(token=res.verification_token, code=code)

    with pytest.raises(EntityAlreadyExistsError, match="already exists"):
        await service.register(
            login="charlie2", password="password123", email="CHARLIE@test.com"
        )


@pytest.mark.anyio
async def test_login_by_login_success(uow, hasher, token_provider):
    service = AuthService(uow=uow, hasher=hasher, token_provider=token_provider)
    reg_res = await service.register(login="david", password="correct_password")
    registered_user = reg_res.user

    user, access_token, refresh_token = await service.login(
        identifier="david", password="correct_password"
    )

    assert user.id == registered_user.id
    assert access_token.startswith(f"access_{user.id}")
    assert refresh_token.startswith(f"refresh_{user.id}")

    # Case-insensitive login check
    user_upper, _, _ = await service.login(
        identifier="DaViD", password="correct_password"
    )
    assert user_upper.id == registered_user.id


@pytest.mark.anyio
async def test_login_by_email_success(uow, hasher, token_provider):
    store = MockVerificationStore()
    queue = MockTaskQueue()
    service = AuthService(
        uow=uow,
        hasher=hasher,
        token_provider=token_provider,
        verification_store=store,
        task_queue=queue,
    )
    reg_res = await service.register(
        login="emma", password="password123", email="emma@domain.com"
    )
    code = queue.sent[0][2]
    registered_user, _ = await service.confirm_verification_code(
        token=reg_res.verification_token, code=code
    )

    user, access_token, refresh_token = await service.login(
        identifier="emma@domain.com", password="password123"
    )

    assert user.id == registered_user.id


@pytest.mark.anyio
async def test_login_invalid_password(uow, hasher, token_provider):
    service = AuthService(uow=uow, hasher=hasher, token_provider=token_provider)
    await service.register(login="frank", password="correct_password")

    with pytest.raises(AuthenticationError, match="Invalid credentials"):
        await service.login(identifier="frank", password="wrong_password")


@pytest.mark.anyio
async def test_login_unknown_user_timing_attack_mitigation(uow, hasher, token_provider):
    service = AuthService(uow=uow, hasher=hasher, token_provider=token_provider)

    initial_verify_count = hasher.verify_call_count
    with pytest.raises(AuthenticationError, match="Invalid credentials"):
        await service.login(identifier="non_existent", password="any_password")

    # Verify that a dummy verify call was executed
    assert hasher.verify_call_count == initial_verify_count + 1


@pytest.mark.anyio
async def test_login_banned_user_forbidden(uow, hasher, token_provider):
    service = AuthService(uow=uow, hasher=hasher, token_provider=token_provider)
    reg = await service.register(login="banned_user", password="password123")
    user = reg.user

    # Add active ban
    ban = UserBanDomain(
        user_id=user.id,
        reason="Cheating",
        created_by=uuid7(),
        ended_at=datetime.now(tz=UTC) + timedelta(days=7),
    )
    await uow.bans.add(ban)

    with pytest.raises(PermissionDeniedError, match="User is banned"):
        await service.login(identifier="banned_user", password="password123")


@pytest.mark.anyio
async def test_verify_access(uow, hasher, token_provider):
    service = AuthService(uow=uow, hasher=hasher, token_provider=token_provider)
    reg = await service.register(login="george", password="password123")
    user = reg.user

    # Non-existent user -> error
    with pytest.raises(AuthenticationError, match="not found or deleted"):
        await service.verify_access(user_id=uuid7())

    # Deleted user -> error
    deleted_user = UserDomain(login="deleted", deleted_at=datetime.now(tz=UTC))
    await uow.users.add(deleted_user)
    with pytest.raises((AuthenticationError, PermissionDeniedError), match="deleted"):
        await service.verify_access(user_id=deleted_user.id)

    # Valid user without special permission
    verified = await service.verify_access(user_id=user.id)
    assert verified.id == user.id

    # Missing permission
    with pytest.raises(PermissionDeniedError, match="Missing required permission"):
        await service.verify_access(
            user_id=user.id, required_permission="admin:dashboard"
        )

    # Add permission
    user.global_permissions = ["admin:dashboard"]
    await uow.users.update(user)
    assert (
        await service.verify_access(
            user_id=user.id, required_permission="admin:dashboard"
        )
    ).id == user.id

    # Wildcard permission gives access to everything
    user.global_permissions = ["*"]
    await uow.users.update(user)
    assert (
        await service.verify_access(user_id=user.id, required_permission="super:action")
    ).id == user.id


@pytest.mark.anyio
async def test_refresh_tokens_with_rotation_and_blacklist(
    uow, hasher, token_provider, blacklist
):
    service = AuthService(
        uow=uow,
        hasher=hasher,
        token_provider=token_provider,
        blacklist=blacklist,
    )
    await service.register(login="refresh_user", password="password123")
    _, _, refresh_token = await service.login(
        identifier="refresh_user", password="password123"
    )

    # First refresh succeeds and rotates
    _, _, new_refresh = await service.refresh_tokens(refresh_token=refresh_token)
    assert new_refresh != refresh_token

    # Re-using the old refresh token must be rejected because its jti is blacklisted
    with pytest.raises(AuthenticationError, match="Token has been revoked"):
        await service.refresh_tokens(refresh_token=refresh_token)


@pytest.mark.anyio
async def test_bind_email_user_cooldown(uow, hasher, token_provider):
    vstore = MockVerificationStore()
    service = AuthService(
        uow=uow,
        hasher=hasher,
        token_provider=token_provider,
        verification_store=vstore,
    )
    reg = await service.register(login="cooldown_user", password="password123")
    user = reg.user

    # First bind request succeeds
    token = await service.request_bind_email_code(
        user_id=user.id,
        current_email=None,
        verified_email=False,
        new_email="cooldown1@example.com",
    )
    assert token is not None

    # Immediate second request from same user with different email fails with user cooldown
    with pytest.raises(DomainValidationError, match="cooldown is active for this user"):
        await service.request_bind_email_code(
            user_id=user.id,
            current_email=None,
            verified_email=False,
            new_email="cooldown2@example.com",
        )


@pytest.mark.anyio
async def test_logout_revokes_token(uow, hasher, token_provider, blacklist):
    service = AuthService(
        uow=uow,
        hasher=hasher,
        token_provider=token_provider,
        blacklist=blacklist,
    )
    await service.register(login="logout_user", password="password123")
    _, _, refresh_token = await service.login(
        identifier="logout_user", password="password123"
    )

    # Logout revokes refresh token
    await service.logout(refresh_token=refresh_token)

    # Attempting to refresh with logged out token fails
    with pytest.raises(AuthenticationError, match="Token has been revoked"):
        await service.refresh_tokens(refresh_token=refresh_token)
