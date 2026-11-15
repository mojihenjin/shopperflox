import hashlib
import hmac
from decimal import Decimal

import pytest
from uuid6 import uuid7

from src.application.services import PaymentService
from src.domain.exceptions import AuthenticationError, DomainValidationError
from src.domain.models import (
    OrderDomain,
    OrderStatus,
    PaymentDomain,
    PaymentStatus,
)

pytestmark = pytest.mark.anyio


def make_sig(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def test_payment_webhook_flow(order_uow):
    secret = "my_secret_key"
    service = PaymentService(uow=order_uow, webhook_secret=secret)
    user_id = uuid7()
    order_id = uuid7()

    # Create pending order and payment
    order = OrderDomain(
        id=order_id,
        user_id=user_id,
        total_amount=Decimal("100.00"),
        shipping_address={"city": "Paris"},
        status=OrderStatus.PENDING_PAYMENT,
        created_by=user_id,
    )
    await order_uow.orders.add(order)

    payment = PaymentDomain(
        order_id=order_id,
        provider="stripe",
        amount=Decimal("100.00"),
        status=PaymentStatus.PENDING,
        created_by=user_id,
    )
    await order_uow.payments.add(payment)

    raw_body = b'{"status": "succeeded"}'
    valid_sig = make_sig(secret, raw_body)

    # 1. Invalid signature raises AuthenticationError
    with pytest.raises(AuthenticationError, match="Invalid webhook signature"):
        await service.process_webhook(
            raw_body=raw_body,
            signature="wrong_sig",
            order_id=order_id,
            external_transaction_id="tx_123",
            status="succeeded",
            paid_amount=Decimal("100.00"),
        )

    # 2. Paid amount mismatch raises DomainValidationError
    with pytest.raises(DomainValidationError, match="does not match order total"):
        await service.process_webhook(
            raw_body=raw_body,
            signature=valid_sig,
            order_id=order_id,
            external_transaction_id="tx_123",
            status="succeeded",
            paid_amount=Decimal("50.00"),
        )

    # 3. Successful webhook execution
    res = await service.process_webhook(
        raw_body=raw_body,
        signature=valid_sig,
        order_id=order_id,
        external_transaction_id="tx_123",
        status="succeeded",
        paid_amount=Decimal("100.00"),
    )
    assert res.status == PaymentStatus.SUCCEEDED
    assert res.external_id == "tx_123"

    updated_order = await order_uow.orders.get_by_id(order_id)
    assert updated_order.status == OrderStatus.PAID

    # 4. Idempotency: repeating same webhook returns payment without error
    repeat_res = await service.process_webhook(
        raw_body=raw_body,
        signature=valid_sig,
        order_id=order_id,
        external_transaction_id="tx_123",
        status="succeeded",
        paid_amount=Decimal("100.00"),
    )
    assert repeat_res.status == PaymentStatus.SUCCEEDED
