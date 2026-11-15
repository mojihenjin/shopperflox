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
