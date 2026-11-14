import pytest
from uuid6 import uuid7

from src.application.services import UserService
from src.domain.exceptions import (
    AuthenticationError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from src.domain.models import UserDomain, UserPersonalDomain
from src.utils import factory_now

pytestmark = pytest.mark.anyio


@pytest.fixture
def user_service(uow) -> UserService:
    return UserService(uow)


@pytest.fixture
async def sample_user(uow) -> UserDomain:
    user = UserDomain(
        id=uuid7(),
        login="regular_user",
        email="regular@example.com",
        global_permissions=[],
    )
    await uow.users.add(user)
    return user


@pytest.fixture
async def admin_user(uow) -> UserDomain:
    admin = UserDomain(
        id=uuid7(),
        login="admin_user",
        email="admin@example.com",
        global_permissions=["users:read", "users:write", "users:delete"],
    )
    await uow.users.add(admin)
    return admin


@pytest.fixture
async def stranger_user(uow) -> UserDomain:
    stranger = UserDomain(
        id=uuid7(),
        login="stranger_user",
        email="stranger@example.com",
        global_permissions=[],
    )
    await uow.users.add(stranger)
    return stranger


async def test_get_user_profile_self(user_service, sample_user, uow):
    personal = UserPersonalDomain(
        id=sample_user.id,
        created_by=sample_user.id,
        firstname="John",
        lastname="Doe",
        phone_number="+1234567890",
    )
    await uow.personal.add(personal)

    user, profile = await user_service.get_user_profile(
        actor_id=sample_user.id, target_user_id=sample_user.id
    )

    assert user.id == sample_user.id
    assert profile is not None
    assert profile.firstname == "John"
    assert profile.lastname == "Doe"


async def test_get_user_profile_by_admin(user_service, sample_user, admin_user, uow):
    user, profile = await user_service.get_user_profile(
        actor_id=admin_user.id, target_user_id=sample_user.id
    )
    assert user.id == sample_user.id
    assert profile is None


async def test_get_user_profile_by_stranger_denied(
    user_service, sample_user, stranger_user
):
    with pytest.raises(PermissionDeniedError, match="Access denied to user resource"):
        await user_service.get_user_profile(
            actor_id=stranger_user.id, target_user_id=sample_user.id
        )


async def test_get_user_profile_actor_not_found_or_deleted(
    user_service, sample_user, uow
):
    with pytest.raises(AuthenticationError, match="Actor user not found or deleted"):
        await user_service.get_user_profile(
            actor_id=uuid7(), target_user_id=sample_user.id
        )

    sample_user.deleted_at = factory_now()
    await uow.users.update(sample_user)
    with pytest.raises(AuthenticationError, match="Actor user not found or deleted"):
        await user_service.get_user_profile(
            actor_id=sample_user.id, target_user_id=sample_user.id
        )


async def test_get_user_profile_target_not_found(user_service, admin_user):
    with pytest.raises(EntityNotFoundError, match="User not found"):
        await user_service.get_user_profile(
            actor_id=admin_user.id, target_user_id=uuid7()
        )


async def test_update_personal_create_and_update(user_service, sample_user):
    # Initial creation of personal profile
    personal = await user_service.update_personal(
        actor_id=sample_user.id,
        target_user_id=sample_user.id,
        firstname="Alice",
        lastname="Smith",
        phone_number="+1000000001",
    )
    assert personal.id == sample_user.id
    assert personal.firstname == "Alice"
    assert personal.phone_number == "+1000000001"

    # Updating existing profile
    updated = await user_service.update_personal(
        actor_id=sample_user.id,
        target_user_id=sample_user.id,
        firstname="Alice Updated",
        lastname=None,
        phone_number="+1000000001",
    )
    assert updated.firstname == "Alice Updated"
    assert updated.lastname is None
    assert updated.updated_at is not None


async def test_update_personal_phone_collision(
    user_service, sample_user, stranger_user, uow
):
    # stranger already has this phone number
    stranger_personal = UserPersonalDomain(
        id=stranger_user.id,
        created_by=stranger_user.id,
        firstname="Stranger",
        lastname="User",
        phone_number="+1000000002",
    )
    await uow.personal.add(stranger_personal)

    with pytest.raises(
        EntityAlreadyExistsError,
        match="Phone number '\\+1000000002' is already registered",
    ):
        await user_service.update_personal(
            actor_id=sample_user.id,
            target_user_id=sample_user.id,
            firstname="Alice",
            lastname="Smith",
            phone_number="+1000000002",
        )


async def test_update_personal_stranger_denied(
    user_service, sample_user, stranger_user
):
    with pytest.raises(PermissionDeniedError, match="Access denied to user resource"):
        await user_service.update_personal(
            actor_id=stranger_user.id,
            target_user_id=sample_user.id,
            firstname="Hacker",
            lastname="Attack",
            phone_number="+1999999999",
        )


async def test_add_address_first_is_always_default(user_service, sample_user):
    # Even if is_default=False, the first address should become default
    addr1 = await user_service.add_address(
        actor_id=sample_user.id,
        target_user_id=sample_user.id,
        city="Moscow",
        street="Tverskaya 1",
        postal_code="101000",
        is_default=False,
    )
    assert addr1.is_default is True

    # Second address with is_default=False remains non-default
    addr2 = await user_service.add_address(
        actor_id=sample_user.id,
        target_user_id=sample_user.id,
        city="Saint Petersburg",
        street="Nevsky 10",
        postal_code="190000",
        is_default=False,
    )
    assert addr2.is_default is False
    assert addr1.is_default is True

    # Third address with is_default=True unsets previous default
    addr3 = await user_service.add_address(
        actor_id=sample_user.id,
        target_user_id=sample_user.id,
        city="Kazan",
        street="Baumana 5",
        postal_code="420000",
        is_default=True,
    )
    assert addr3.is_default is True
    assert addr1.is_default is False


async def test_set_default_address(user_service, sample_user):
    addr1 = await user_service.add_address(
        actor_id=sample_user.id,
        target_user_id=sample_user.id,
        city="Moscow",
        street="Tverskaya 1",
        postal_code="101000",
    )
    addr2 = await user_service.add_address(
        actor_id=sample_user.id,
        target_user_id=sample_user.id,
        city="Saint Petersburg",
        street="Nevsky 10",
        postal_code="190000",
        is_default=False,
    )
    assert addr1.is_default is True
    assert addr2.is_default is False

    updated_addr2 = await user_service.set_default_address(
        actor_id=sample_user.id,
        target_user_id=sample_user.id,
        address_id=addr2.id,
    )
    assert updated_addr2.is_default is True
    assert addr1.is_default is False


async def test_set_default_address_idor_protection(
    user_service, sample_user, stranger_user
):
    stranger_addr = await user_service.add_address(
        actor_id=stranger_user.id,
        target_user_id=stranger_user.id,
        city="City",
        street="Street",
        postal_code="123456",
    )

    with pytest.raises(EntityNotFoundError, match="Address not found"):
        await user_service.set_default_address(
            actor_id=sample_user.id,
            target_user_id=sample_user.id,
            address_id=stranger_addr.id,
        )


async def test_delete_address(user_service, sample_user, uow):
    addr = await user_service.add_address(
        actor_id=sample_user.id,
        target_user_id=sample_user.id,
        city="Moscow",
        street="Tverskaya 1",
        postal_code="101000",
    )
    assert await uow.addresses.get_by_id(addr.id) is not None

    await user_service.delete_address(
        actor_id=sample_user.id,
        target_user_id=sample_user.id,
        address_id=addr.id,
    )
    assert await uow.addresses.get_by_id(addr.id) is None


async def test_delete_address_idor_protection(user_service, sample_user, stranger_user):
    stranger_addr = await user_service.add_address(
        actor_id=stranger_user.id,
        target_user_id=stranger_user.id,
        city="City",
        street="Street",
        postal_code="123456",
    )

    with pytest.raises(EntityNotFoundError, match="Address not found"):
        await user_service.delete_address(
            actor_id=sample_user.id,
            target_user_id=sample_user.id,
            address_id=stranger_addr.id,
        )


async def test_soft_delete_user(user_service, sample_user, admin_user):
    await user_service.soft_delete_user(
        actor_id=admin_user.id, target_user_id=sample_user.id
    )
    assert sample_user.is_deleted is True
    assert sample_user.deleted_at is not None

    # Deleting already deleted user raises EntityNotFoundError
    with pytest.raises(EntityNotFoundError, match="User not found"):
        await user_service.soft_delete_user(
            actor_id=admin_user.id, target_user_id=sample_user.id
        )


async def test_soft_delete_user_denied_stranger(
    user_service, sample_user, stranger_user
):
    with pytest.raises(PermissionDeniedError, match="Access denied to user resource"):
        await user_service.soft_delete_user(
            actor_id=stranger_user.id, target_user_id=sample_user.id
        )
