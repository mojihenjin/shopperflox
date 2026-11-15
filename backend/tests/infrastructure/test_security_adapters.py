import secrets

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
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
    assert callable(hasher.verify_dummy)


def test_argon2_hash_and_verify():
    hasher = Argon2PasswordHasher()
    password = "SuperSecretPassword123!"

    hashed = hasher.hash(password)
    assert hashed.startswith("$argon2")
    assert hashed != password

    assert hasher.verify(password, hashed) is True
    assert hasher.verify("WrongPassword", hashed) is False


def test_argon2_pepper_isolation():
    hasher1 = Argon2PasswordHasher(pepper="pepper-one")
    hasher2 = Argon2PasswordHasher(pepper="pepper-two")
    password = "SuperSecretPassword123!"

    hash1 = hasher1.hash(password)
    hash2 = hasher2.hash(password)
    assert hash1 != hash2

    assert hasher1.verify(password, hash1) is True
    assert hasher2.verify(password, hash1) is False


@pytest.mark.anyio
async def test_argon2_verify_dummy():
    hasher = Argon2PasswordHasher()
    await hasher.verify_dummy("any_password")


def test_argon2_corrupted_hash_returns_false():
    hasher = Argon2PasswordHasher()
    assert hasher.verify("secret", "not_a_valid_argon2_hash") is False
    assert (
        hasher.verify("secret", "$argon2id$v=19$m=65536,t=3,p=4$corrupted$hash")
        is False
    )


def test_jwt_provider_implements_protocol():
    provider: TokenProviderProtocol = JwtTokenProvider()
    assert callable(provider.create_access_token)
    assert callable(provider.create_refresh_token)
    assert callable(provider.decode_token)


def test_jwt_eddsa_default_from_settings():
    # By default, JwtTokenProvider uses EdDSA with keys from settings (.env)
    provider = JwtTokenProvider()
    assert provider.algorithm == "EdDSA"

    user_id = uuid7()
    permissions = ["users:read", "users:write"]

    access_token = provider.create_access_token(user_id, permissions)
    assert isinstance(access_token, str)

    payload = provider.decode_token(access_token, expected_type="access")
    assert payload["sub"] == str(user_id)
    assert payload["permissions"] == permissions
    assert payload["type"] == "access"
    assert "jti" in payload

    refresh_token = provider.create_refresh_token(user_id)
    payload_refresh = provider.decode_token(refresh_token, expected_type="refresh")
    assert payload_refresh["sub"] == str(user_id)
    assert payload_refresh["type"] == "refresh"
    assert "jti" in payload_refresh


def test_jwt_eddsa_hex_keys():
    seed = secrets.token_bytes(32)
    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
    pub_key = priv_key.public_key()
    priv_hex = seed.hex()
    pub_hex = pub_key.public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()

    provider = JwtTokenProvider(
        private_key=priv_hex,
        public_key=pub_hex,
        algorithm="EdDSA",
    )
    user_id = uuid7()
    token = provider.create_access_token(user_id, ["admin"])
    payload = provider.decode_token(token, expected_type="access")
    assert payload["sub"] == str(user_id)
    assert payload["permissions"] == ["admin"]


def test_jwt_eddsa_pem_keys():
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pem_priv = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pem_pub = pub.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    provider = JwtTokenProvider(
        private_key=pem_priv,
        public_key=pem_pub,
        algorithm="EdDSA",
    )
    user_id = uuid7()
    token = provider.create_access_token(user_id, ["editor"])
    payload = provider.decode_token(token, expected_type="access")
    assert payload["sub"] == str(user_id)
    assert payload["permissions"] == ["editor"]


def test_jwt_eddsa_verification_only_provider():
    priv = ed25519.Ed25519PrivateKey.generate()
    pub_hex = (
        priv.public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        .hex()
    )

    signer = JwtTokenProvider(private_key=priv, algorithm="EdDSA")
    verifier = JwtTokenProvider(public_key=pub_hex, algorithm="EdDSA")

    user_id = uuid7()
    token = signer.create_access_token(user_id, ["reader"])

    # Verifier with only public key can decode
    payload = verifier.decode_token(token, expected_type="access")
    assert payload["sub"] == str(user_id)

    # Verifier without private key cannot sign
    with pytest.raises(
        ValueError, match="Private key is required to sign JWT tokens with EdDSA"
    ):
        verifier.create_access_token(user_id, ["reader"])


def test_jwt_eddsa_wrong_key_fails():
    priv1 = ed25519.Ed25519PrivateKey.generate()
    priv2 = ed25519.Ed25519PrivateKey.generate()

    signer = JwtTokenProvider(private_key=priv1, algorithm="EdDSA")
    wrong_verifier = JwtTokenProvider(public_key=priv2.public_key(), algorithm="EdDSA")

    user_id = uuid7()
    token = signer.create_access_token(user_id, [])

    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        wrong_verifier.decode_token(token)


def test_jwt_wrong_type_token_rejected():
    provider = JwtTokenProvider()
    user_id = uuid7()

    refresh_token = provider.create_refresh_token(user_id)
    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        provider.decode_token(refresh_token, expected_type="access")

    access_token = provider.create_access_token(user_id, ["read"])
    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        provider.decode_token(access_token, expected_type="refresh")


def test_jwt_tampered_token():
    provider = JwtTokenProvider()
    user_id = uuid7()

    token = provider.create_access_token(user_id, [])
    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        provider.decode_token(token + "tampered")


def test_jwt_expired_token():
    provider = JwtTokenProvider(access_ttl_minutes=-1)
    user_id = uuid7()
    token = provider.create_access_token(user_id, [])

    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        provider.decode_token(token)


def test_jwt_symmetric_hs256_backward_compatibility():
    provider = JwtTokenProvider(
        secret_key=SECRET_KEY_32,
        algorithm="HS256",
        access_ttl_minutes=10,
    )
    user_id = uuid7()
    token = provider.create_access_token(user_id, ["test"])
    payload = provider.decode_token(token, expected_type="access")
    assert payload["sub"] == str(user_id)
    assert payload["permissions"] == ["test"]


def test_jwt_fail_fast_when_missing_keys(monkeypatch):
    from src.core import settings

    monkeypatch.setattr(settings, "jwt_private_key", "")
    monkeypatch.setattr(settings, "jwt_public_key", "")
    monkeypatch.setattr(settings, "jwt_secret_key", "")

    with pytest.raises(
        RuntimeError, match="JWT_PRIVATE_KEY is required but not configured"
    ):
        JwtTokenProvider(algorithm="EdDSA")

    with pytest.raises(
        RuntimeError, match="JWT secret key is required but not configured"
    ):
        JwtTokenProvider(algorithm="HS256")
