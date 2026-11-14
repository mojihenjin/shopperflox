import pytest
from uuid6 import uuid7

from src.domain.exceptions import AuthenticationError
from src.domain.interfaces import (
    PasswordHasherProtocol,
    TokenProviderProtocol,
)
from src.infrastructure.security import (
    Argon2PasswordHasher,
    JwtTokenProvider,
)

SECRET_KEY_32 = "super-secret-key-that-is-at-least-32-bytes-long-for-hs256!"
OTHER_KEY_32 = "another-secret-key-that-is-at-least-32-bytes-long-for-hs256!"


def test_argon2_password_hasher_implements_protocol():
    hasher: PasswordHasherProtocol = Argon2PasswordHasher()
    assert callable(hasher.hash)
    assert callable(hasher.verify)


def test_argon2_hash_and_verify():
    hasher = Argon2PasswordHasher()
    password = "SuperSecretPassword123!"

    hashed = hasher.hash(password)
    assert hashed.startswith("$argon2")
    assert hashed != password

    assert hasher.verify(password, hashed) is True
    assert hasher.verify("WrongPassword", hashed) is False


def test_argon2_corrupted_hash_returns_false():
    hasher = Argon2PasswordHasher()
    assert hasher.verify("secret", "not_a_valid_argon2_hash") is False
    assert (
        hasher.verify("secret", "$argon2id$v=19$m=65536,t=3,p=4$corrupted$hash")
        is False
    )


def test_jwt_provider_implements_protocol():
    provider: TokenProviderProtocol = JwtTokenProvider(secret_key=SECRET_KEY_32)
    assert callable(provider.create_access_token)
    assert callable(provider.create_refresh_token)
    assert callable(provider.decode_token)


def test_jwt_create_and_decode_access_token():
    provider = JwtTokenProvider(
        secret_key=SECRET_KEY_32,
        algorithm="HS256",
        access_ttl_minutes=10,
    )
    user_id = uuid7()
    permissions = ["users:read", "users:write"]

    token = provider.create_access_token(user_id, permissions)
    assert isinstance(token, str)

    payload = provider.decode_token(token, expected_type="access")
    assert payload["sub"] == str(user_id)
    assert payload["permissions"] == permissions
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_create_and_decode_refresh_token():
    provider = JwtTokenProvider(
        secret_key=SECRET_KEY_32,
        algorithm="HS256",
        refresh_ttl_days=7,
    )
    user_id = uuid7()

    token = provider.create_refresh_token(user_id)
    assert isinstance(token, str)

    payload = provider.decode_token(token, expected_type="refresh")
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    assert "exp" in payload


def test_jwt_wrong_type_token_rejected():
    provider = JwtTokenProvider(secret_key=SECRET_KEY_32)
    user_id = uuid7()

    refresh_token = provider.create_refresh_token(user_id)

    # Attempting to use refresh token where access token is expected
    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        provider.decode_token(refresh_token, expected_type="access")

    access_token = provider.create_access_token(user_id, ["read"])
    # Attempting to use access token where refresh token is expected
    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        provider.decode_token(access_token, expected_type="refresh")


def test_jwt_tampered_or_invalid_secret():
    provider = JwtTokenProvider(secret_key=SECRET_KEY_32)
    other_provider = JwtTokenProvider(secret_key=OTHER_KEY_32)
    user_id = uuid7()

    token = provider.create_access_token(user_id, [])

    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        other_provider.decode_token(token)

    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        provider.decode_token(token + "tampered")


def test_jwt_expired_token():
    provider = JwtTokenProvider(
        secret_key=SECRET_KEY_32,
        access_ttl_minutes=-1,  # Already expired in the past
    )
    user_id = uuid7()
    token = provider.create_access_token(user_id, [])

    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        provider.decode_token(token)
