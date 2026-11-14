from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.domain.models import (
    UserAddressDomain,
    UserBanDomain,
    UserDomain,
    UserPersonalDomain,
)
from uuid6 import uuid7


def test_user_domain_defaults():
    user = UserDomain(login="john_doe")

    assert isinstance(user.id, UUID)
    assert user.login == "john_doe"
    assert user.email is None
    assert user.password_hash is None
    assert user.verified_profile is False
    assert user.verified_email is False
    assert user.global_permissions == []
    assert user.created_by is None
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)
    assert user.deleted_at is None
    assert user.is_deleted is False


def test_user_domain_is_deleted():
    user = UserDomain(login="alice", deleted_at=datetime.now(tz=UTC))
    assert user.is_deleted is True


def test_user_domain_password_hash_repr():
    user = UserDomain(login="alice", password_hash="secret_hash_value")

    assert "secret_hash_value" not in repr(user)


def test_user_personal_domain():
    user_id = uuid7()
    author_id = uuid7()
    personal = UserPersonalDomain(
        id=user_id,
        created_by=author_id,
        firstname="John",
        lastname="Doe",
        phone_number="+1234567890",
    )

    assert personal.id == user_id
    assert personal.created_by == author_id
    assert personal.firstname == "John"
    assert personal.lastname == "Doe"
    assert personal.phone_number == "+1234567890"


def test_user_ban_domain():
    author_id = uuid7()
    user_id = uuid7()
    ban = UserBanDomain(
        user_id=user_id,
        reason="Spamming",
        created_by=author_id,
    )

    assert isinstance(ban.id, UUID)
    assert ban.user_id == user_id
    assert ban.reason == "Spamming"
    assert ban.ended_at is None
    assert ban.is_active() is True

    # Ban in the future is still active
    ban_future = UserBanDomain(
        user_id=user_id,
        reason="Temp ban",
        created_by=author_id,
        ended_at=datetime.now(tz=UTC) + timedelta(days=1),
    )
    assert ban_future.is_active() is True

    # Expired ban is inactive
    ban_expired = UserBanDomain(
        user_id=user_id,
        reason="Expired ban",
        created_by=author_id,
        ended_at=datetime.now(tz=UTC) - timedelta(days=1),
    )
    assert ban_expired.is_active() is False


def test_user_address_domain():
    author_id = uuid7()
    user_id = uuid7()
    address = UserAddressDomain(
        user_id=user_id,
        city="Moscow",
        street="Tverskaya 1",
        postal_code="101000",
        created_by=author_id,
        is_default=True,
    )

    assert isinstance(address.id, UUID)
    assert address.is_default is True
    assert address.city == "Moscow"
