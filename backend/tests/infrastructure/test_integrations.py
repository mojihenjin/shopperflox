import asyncio
from decimal import Decimal
from pathlib import Path

import pytest
from uuid6 import uuid7

from src.core import Settings
from src.infrastructure.messaging import (
    ConsoleStubEmailTransport,
    TaskiqEmailQueue,
    get_email_transport,
)
from src.infrastructure.payments import StubPaymentGateway
from src.infrastructure.redis.verification import RedisEmailVerificationStore
from src.infrastructure.storage import LocalFileStorage, get_file_storage

pytestmark = pytest.mark.anyio


async def test_local_file_storage(tmp_path: Path):
    storage = LocalFileStorage(local_dir=tmp_path, base_url="/media")
    key = "products/test.png"
    data = b"\x89PNG\r\n\x1a\n"

    url = await storage.upload_file(key=key, data=data, content_type="image/png")
    assert url == "/media/products/test.png"
    assert (tmp_path / "products" / "test.png").exists()

    await storage.delete_file(key=key)
    assert not (tmp_path / "products" / "test.png").exists()


async def test_stub_payment_gateway():
    gateway = StubPaymentGateway()
    order_id = uuid7()
    result = await gateway.create_payment(
        order_id=order_id,
        amount=Decimal("100.00"),
        currency="RUB",
    )
    assert result.external_transaction_id.startswith("stub_")
    assert f"/mock-checkout/{order_id}" in result.confirmation_url


async def test_email_transports_and_queue():
    transport = ConsoleStubEmailTransport()
    await transport.send_email(
        to_email="test@example.com",
        subject="Test",
        body_text="Code: 123-456",
    )

    settings = Settings(email_backend="console", storage_backend="local")
    resolved_transport = get_email_transport(settings)
    assert isinstance(resolved_transport, ConsoleStubEmailTransport)

    resolved_storage = get_file_storage(settings)
    assert isinstance(resolved_storage, LocalFileStorage)

    queue = TaskiqEmailQueue()
    await queue.enqueue_email(
        to_email="test@example.com",
        subject="Taskiq Test",
        body_text="123-456",
    )


async def test_redis_verification_store_concurrent_attempts():
    store = RedisEmailVerificationStore()
    token = f"test_concurrent_{uuid7()}"
    try:
        await store.save_session(
            token, {"flow": "register", "attempts": 0, "code": "123-456"}
        )

        # 10 parallel attempts via asyncio.gather
        results = await asyncio.gather(
            *[store.increment_attempts(token) for _ in range(10)]
        )
        sorted_res = sorted(results)

        # Exactly 5 attempts processed (1..5) and 5 got -1 because session was atomically destroyed
        assert sorted_res == [-1, -1, -1, -1, -1, 1, 2, 3, 4, 5]

        # Session is deleted in Redis
        session = await store.get_session(token)
        assert session is None
    finally:
        await store.delete_session(token)
        await store.aclose()


async def test_redis_verification_store_user_cooldown():
    store = RedisEmailVerificationStore()
    user_id = uuid7()
    try:
        first = await store.check_and_set_user_cooldown(user_id, ttl_seconds=60)
        assert first is True

        second = await store.check_and_set_user_cooldown(user_id, ttl_seconds=60)
        assert second is False
    finally:
        key = f"email_verify_user_cooldown:{user_id}"
        await store._client.delete(key)
        await store.aclose()
