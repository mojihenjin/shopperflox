import logging

import pytest

from src.core.logging import setup_logging
from src.core.settings import Settings
from src.infrastructure.db.session import create_engine
from src.infrastructure.security.password import Argon2PasswordHasher


def test_enduro_attack_production_failsafe():
    # Production + enduro_attack=True must raise ValueError
    with pytest.raises(ValueError, match="strictly prohibited"):
        Settings(
            app_env="production",
            enduro_attack=True,
            webhook_secret="a" * 32,
            jwt_private_key="test_private_key",
        )

    # Valid configurations
    dev_settings = Settings(app_env="dev", enduro_attack=True)
    assert dev_settings.enduro_attack is True

    test_settings = Settings(app_env="test", enduro_attack=True)
    assert test_settings.enduro_attack is True

    prod_settings = Settings(
        app_env="production",
        enduro_attack=False,
        webhook_secret="secure_prod_webhook_secret_string_32",
        jwt_private_key="prod_ed25519_private_key_content",
    )
    assert prod_settings.enduro_attack is False


def test_production_secrets_validation():
    # Default webhook_secret rejected in production
    with pytest.raises(ValueError, match="WEBHOOK_SECRET"):
        Settings(
            app_env="production",
            webhook_secret="dev_webhook_secret",
            jwt_private_key="valid_key",
        )

    # Empty / short webhook_secret rejected in production
    with pytest.raises(ValueError, match="WEBHOOK_SECRET"):
        Settings(
            app_env="production",
            webhook_secret="short_secret",
            jwt_private_key="valid_key",
        )

    # Asymmetric (default EdDSA) without private key rejected in production
    with pytest.raises(ValueError, match="JWT_PRIVATE_KEY"):
        Settings(
            app_env="production",
            webhook_secret="a" * 32,
            jwt_private_key="",
        )

    # Symmetric HS256 with default or short secret key rejected in production
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(
            app_env="production",
            jwt_algorithm="HS256",
            jwt_secret_key="insecure-secret-key-change-me",
            webhook_secret="a" * 32,
        )

    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(
            app_env="production",
            jwt_algorithm="HS256",
            jwt_secret_key="short",
            webhook_secret="a" * 32,
        )

    # Valid symmetric production configuration
    prod_sym = Settings(
        app_env="production",
        jwt_algorithm="HS256",
        jwt_secret_key="a" * 32,
        webhook_secret="b" * 32,
    )
    assert prod_sym.app_env == "production"


def test_enduro_attack_lightweight_hasher(monkeypatch):
    from src.core import settings

    monkeypatch.setattr(settings, "enduro_attack", True)
    hasher = Argon2PasswordHasher()

    # The internal hasher should have lightweight parameters
    internal_argon2 = hasher._hasher.hashers[0]
    assert internal_argon2._hasher.time_cost == 1
    assert internal_argon2._hasher.memory_cost == 1024
    assert internal_argon2._hasher.parallelism == 1

    # Verify hashing & verifying works properly
    h = hasher.hash("TestPass123!")
    assert hasher.verify("TestPass123!", h) is True


def test_enduro_attack_logging_level_raised(monkeypatch):
    test_settings = Settings(app_env="dev", enduro_attack=True, log_level="INFO")
    setup_logging(test_settings)
    assert logging.root.level == logging.WARNING


def test_enduro_attack_database_pool_increased(monkeypatch):
    from src.core import settings

    monkeypatch.setattr(settings, "enduro_attack", True)
    engine = create_engine("postgresql+asyncpg://user:pass@localhost:5432/testdb")
    assert engine.pool.size() == 30
    assert engine.pool._max_overflow == 20
