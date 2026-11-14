from datetime import timedelta

import pytest
from uuid6 import uuid7

from src.application.services import UserModerationService
from src.domain.exceptions import (
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from src.domain.models import UserDomain
from src.utils import factory_now

pytestmark = pytest.mark.anyio


@pytest.fixture
def moderation_service(uow) -> UserModerationService:
    return UserModerationService(uow)


@pytest.fixture
async def moderator(uow) -> UserDomain:
    mod = UserDomain(
        id=uuid7(),
        login="mod_user",
        email="mod@example.com",
        global_permissions=["users:ban", "users:permissions"],
    )
    await uow.users.add(mod)
    return mod


@pytest.fixture
async def regular_user(uow) -> UserDomain:
    user = UserDomain(
        id=uuid7(),
        login="target_user",
        email="target@example.com",
        global_permissions=[],
    )
    await uow.users.add(user)
    return user


async def test_ban_user_self_ban_forbidden(moderation_service, moderator):
    with pytest.raises(DomainValidationError, match="Cannot ban yourself"):
        await moderation_service.ban_user(
            moderator_id=moderator.id,
            target_user_id=moderator.id,
            reason="Testing self ban",
        )


async def test_ban_user_permission_denied(moderation_service, regular_user, moderator):
    with pytest.raises(PermissionDeniedError, match="Permission 'users:ban' required"):
        await moderation_service.ban_user(
            moderator_id=regular_user.id,
            target_user_id=moderator.id,
            reason="Revenge ban",
        )


async def test_ban_user_target_not_found(moderation_service, moderator):
    with pytest.raises(EntityNotFoundError, match="Target user not found"):
        await moderation_service.ban_user(
            moderator_id=moderator.id,
            target_user_id=uuid7(),
            reason="Ghost user",
        )


async def test_ban_user_success(moderation_service, moderator, regular_user, uow):
    ban_end = factory_now() + timedelta(days=7)
    ban = await moderation_service.ban_user(
        moderator_id=moderator.id,
        target_user_id=regular_user.id,
        reason="Spamming chat",
        ended_at=ban_end,
    )
    assert ban.user_id == regular_user.id
    assert ban.reason == "Spamming chat"
    assert ban.ended_at == ban_end
    assert ban.created_by == moderator.id
    assert uow.committed is True

    # Active ban can be retrieved
    stored_ban = await uow.bans.get_active_by_user_id(regular_user.id)
    assert stored_ban is not None
    assert stored_ban.id == ban.id


async def test_ban_user_already_banned(moderation_service, moderator, regular_user):
    await moderation_service.ban_user(
        moderator_id=moderator.id,
        target_user_id=regular_user.id,
        reason="First ban",
    )

    with pytest.raises(
        EntityAlreadyExistsError, match="User is already actively banned"
    ):
        await moderation_service.ban_user(
            moderator_id=moderator.id,
            target_user_id=regular_user.id,
            reason="Second ban attempt",
        )


async def test_unban_user_success(moderation_service, moderator, regular_user, uow):
    await moderation_service.ban_user(
        moderator_id=moderator.id,
        target_user_id=regular_user.id,
        reason="Temporary ban",
    )
    assert await uow.bans.get_active_by_user_id(regular_user.id) is not None

    unbanned = await moderation_service.unban_user(
        moderator_id=moderator.id,
        target_user_id=regular_user.id,
    )
    assert unbanned.user_id == regular_user.id
    assert unbanned.ended_at is not None
    assert unbanned.is_active() is False

    # No longer active
    assert await uow.bans.get_active_by_user_id(regular_user.id) is None


async def test_unban_user_no_active_ban(moderation_service, moderator, regular_user):
    with pytest.raises(EntityNotFoundError, match="No active ban found for user"):
        await moderation_service.unban_user(
            moderator_id=moderator.id,
            target_user_id=regular_user.id,
        )


async def test_set_permissions_success(
    moderation_service, moderator, regular_user, uow
):
    perms = ["users:read", "products:read", "users:read", "orders:manage"]
    updated_user = await moderation_service.set_permissions(
        admin_id=moderator.id,
        target_user_id=regular_user.id,
        permissions=perms,
    )
    # Deduplicated while preserving order
    assert updated_user.global_permissions == [
        "users:read",
        "products:read",
        "orders:manage",
    ]
    assert uow.committed is True


async def test_set_permissions_permission_denied(
    moderation_service, regular_user, moderator
):
    with pytest.raises(
        PermissionDeniedError, match="Permission 'users:permissions' required"
    ):
        await moderation_service.set_permissions(
            admin_id=regular_user.id,
            target_user_id=moderator.id,
            permissions=["*"],
        )
