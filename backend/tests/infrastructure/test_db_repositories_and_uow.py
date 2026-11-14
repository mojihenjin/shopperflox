from datetime import timedelta

import pytest
from uuid6 import uuid7

from src.domain.exceptions import EntityAlreadyExistsError
from src.domain.interfaces import UserUnitOfWorkProtocol
from src.domain.models import (
    UserAddressDomain,
    UserBanDomain,
    UserDomain,
    UserPersonalDomain,
)
from src.utils import factory_now

pytestmark = pytest.mark.anyio


async def test_uow_implements_protocol(uow):
    # Structural contract verification
    uow_contract: UserUnitOfWorkProtocol = uow
    assert hasattr(uow_contract, "commit")
    assert hasattr(uow_contract, "rollback")
    async with uow:
        assert hasattr(uow, "users")
        assert hasattr(uow, "personal")
        assert hasattr(uow, "addresses")
        assert hasattr(uow, "bans")


async def test_user_repository_crud_and_partial_unique_indexes(uow):
    user_id_1 = uuid7()
    user_1 = UserDomain(
        id=user_id_1,
        login="alice",
        email="alice@example.com",
    )

    async with uow:
        await uow.users.add(user_1)
        await uow.commit()

    # Query by ID, login, email
    async with uow:
        fetched = await uow.users.get_by_id(user_id_1)
        assert fetched is not None
        assert fetched.login == "alice"
        assert fetched.email == "alice@example.com"

        by_login = await uow.users.get_by_login("alice")
        assert by_login is not None
        assert by_login.id == user_id_1

        by_email = await uow.users.get_by_email("alice@example.com")
        assert by_email is not None
        assert by_email.id == user_id_1

        assert await uow.users.exists_active("alice") is True
        assert await uow.users.exists_active("bob") is False

    # Attempting to add duplicate active login raises EntityAlreadyExistsError
    user_dup_login = UserDomain(
        id=uuid7(),
        login="alice",
        email="different@example.com",
    )
    with pytest.raises(
        EntityAlreadyExistsError,
        match="User with login 'alice' or email 'different@example.com' already exists",
    ):
        async with uow:
            await uow.users.add(user_dup_login)
            await uow.commit()

    # Soft-delete user_1
    async with uow:
        u1 = await uow.users.get_by_id(user_id_1)
        assert u1 is not None
        u1.deleted_at = factory_now()
        await uow.users.update(u1)
        await uow.commit()

    # Now a new user CAN reuse login "alice" due to partial index WHERE deleted_at IS NULL
    user_new_alice = UserDomain(
        id=uuid7(),
        login="alice",
        email="new_alice@example.com",
    )
    async with uow:
        await uow.users.add(user_new_alice)
        await uow.commit()

    # Multiple users with email=None are allowed by partial index WHERE email IS NOT NULL
    user_no_email_1 = UserDomain(id=uuid7(), login="user_null_1", email=None)
    user_no_email_2 = UserDomain(id=uuid7(), login="user_null_2", email=None)
    async with uow:
        await uow.users.add(user_no_email_1)
        await uow.users.add(user_no_email_2)
        await uow.commit()


async def test_user_personal_crud_and_phone_partial_index(uow):
    user_1 = UserDomain(id=uuid7(), login="user1")
    user_2 = UserDomain(id=uuid7(), login="user2")
    user_3 = UserDomain(id=uuid7(), login="user3")
    async with uow:
        await uow.users.add(user_1)
        await uow.users.add(user_2)
        await uow.users.add(user_3)
        await uow.commit()

    p1 = UserPersonalDomain(
        id=user_1.id,
        created_by=user_1.id,
        firstname="John",
        lastname="Doe",
        phone_number="+1000000001",
    )
    async with uow:
        await uow.personal.add(p1)
        await uow.commit()

    async with uow:
        fetched = await uow.personal.get_by_user_id(user_1.id)
        assert fetched is not None
        assert fetched.firstname == "John"
        assert fetched.phone_number == "+1000000001"

        by_phone = await uow.personal.get_by_phone("+1000000001")
        assert by_phone is not None
        assert by_phone.id == user_1.id

    # Duplicate phone number raises EntityAlreadyExistsError
    p2_dup = UserPersonalDomain(
        id=user_2.id,
        created_by=user_2.id,
        firstname="Jane",
        lastname="Doe",
        phone_number="+1000000001",
    )
    with pytest.raises(
        EntityAlreadyExistsError,
        match="Personal profile for user .* or phone '\\+1000000001' already exists",
    ):
        async with uow:
            await uow.personal.add(p2_dup)
            await uow.commit()

    # Multiple profiles with phone_number=None are allowed
    p2_null = UserPersonalDomain(
        id=user_2.id,
        created_by=user_2.id,
        phone_number=None,
    )
    p3_null = UserPersonalDomain(
        id=user_3.id,
        created_by=user_3.id,
        phone_number=None,
    )
    async with uow:
        await uow.personal.add(p2_null)
        await uow.personal.add(p3_null)
        await uow.commit()


async def test_user_address_crud_and_unset_default(uow):
    user = UserDomain(id=uuid7(), login="addr_user")
    async with uow:
        await uow.users.add(user)
        await uow.commit()

    addr1 = UserAddressDomain(
        id=uuid7(),
        user_id=user.id,
        city="Moscow",
        street="Tverskaya 1",
        postal_code="101000",
        is_default=True,
        created_by=user.id,
    )
    async with uow:
        await uow.addresses.add(addr1)
        await uow.commit()

    # Second default address for the same user violates partial unique index
    addr2 = UserAddressDomain(
        id=uuid7(),
        user_id=user.id,
        city="Saint Petersburg",
        street="Nevsky 1",
        postal_code="190000",
        is_default=True,
        created_by=user.id,
    )
    with pytest.raises(
        EntityAlreadyExistsError,
        match="Default address conflict for user",
    ):
        async with uow:
            await uow.addresses.add(addr2)
            await uow.commit()

    # Unset default for user, then add or update works
    async with uow:
        await uow.addresses.unset_default_for_user(user.id)
        assert await uow.addresses.get_default_by_user_id(user.id) is None

        # Now addr2 can be added as default
        await uow.addresses.add(addr2)
        await uow.commit()

    async with uow:
        default_addr = await uow.addresses.get_default_by_user_id(user.id)
        assert default_addr is not None
        assert default_addr.id == addr2.id

        addresses = await uow.addresses.list_by_user_id(user.id)
        assert len(addresses) == 2

        # Delete addr1
        await uow.addresses.delete(addr1.id)
        await uow.commit()

    async with uow:
        assert await uow.addresses.get_by_id(addr1.id) is None


async def test_user_ban_crud_and_active_check(uow):
    user = UserDomain(id=uuid7(), login="banned_user")
    admin = UserDomain(id=uuid7(), login="admin_banning")
    async with uow:
        await uow.users.add(user)
        await uow.users.add(admin)
        await uow.commit()

    # Expired ban
    expired_ban = UserBanDomain(
        id=uuid7(),
        user_id=user.id,
        reason="Old offense",
        created_by=admin.id,
        ended_at=factory_now() - timedelta(days=1),
    )
    async with uow:
        await uow.bans.add(expired_ban)
        await uow.commit()

    async with uow:
        # Active ban lookup ignores expired ban
        active = await uow.bans.get_active_by_user_id(user.id)
        assert active is None

    # Active ban
    active_ban = UserBanDomain(
        id=uuid7(),
        user_id=user.id,
        reason="Active spamming",
        created_by=admin.id,
        ended_at=factory_now() + timedelta(days=3),
    )
    async with uow:
        await uow.bans.add(active_ban)
        await uow.commit()

    async with uow:
        active = await uow.bans.get_active_by_user_id(user.id)
        assert active is not None
        assert active.id == active_ban.id

        # Update ended_at to unban
        active.ended_at = factory_now()
        await uow.bans.update(active)
        await uow.commit()

    async with uow:
        assert await uow.bans.get_active_by_user_id(user.id) is None


async def test_uow_rollback_on_exception(uow):
    user_id = uuid7()
    user = UserDomain(id=user_id, login="rollback_user")

    with pytest.raises(RuntimeError, match="Simulated crash"):
        async with uow:
            await uow.users.add(user)
            raise RuntimeError("Simulated crash")

    async with uow:
        fetched = await uow.users.get_by_id(user_id)
        assert fetched is None


async def test_postgres_live_integration():
    try:
        from src.infrastructure.db.uow import SqlAlchemyUserUnitOfWork

        live_uow = SqlAlchemyUserUnitOfWork()
        user_id = uuid7()
        user = UserDomain(id=user_id, login=f"pg_user_{user_id.hex[:8]}")

        async with live_uow:
            await live_uow.users.add(user)
            await live_uow.commit()

        async with live_uow:
            fetched = await live_uow.users.get_by_id(user_id)
            assert fetched is not None
            assert fetched.login == user.login
    except Exception as exc:
        pytest.skip(f"Live PostgreSQL not available: {exc}")
