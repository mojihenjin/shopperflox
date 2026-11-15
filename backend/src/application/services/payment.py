import hashlib
import hmac
import logging
from decimal import Decimal
from typing import Literal
from uuid import UUID

from src.domain.exceptions import (
    AuthenticationError,
    DomainValidationError,
    EntityNotFoundError,
)
from src.domain.interfaces import OrderUnitOfWorkProtocol
from src.domain.models import OrderStatus, PaymentDomain, PaymentStatus

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, uow: OrderUnitOfWorkProtocol, webhook_secret: str) -> None:
        self.uow = uow
        self.webhook_secret = webhook_secret

    def verify_signature(self, raw_body: bytes, signature: str) -> bool:
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def process_webhook(
        self,
        raw_body: bytes,
        signature: str,
        *,
        order_id: UUID,
        external_transaction_id: str,
        status: Literal["succeeded", "failed"],
        paid_amount: Decimal,
    ) -> PaymentDomain:
        if not self.verify_signature(raw_body, signature):
            raise AuthenticationError("Invalid webhook signature")

        async with self.uow:
            payment = await self.uow.payments.get_by_order_id(order_id, for_update=True)
            if payment is None:
                raise EntityNotFoundError("Payment not found for order")

            order = await self.uow.orders.get_by_id(order_id, for_update=True)
            if order is None:
                raise EntityNotFoundError("Order not found")

            # Check if this is a late webhook for an already cancelled order or failed payment
            if status == "succeeded" and (
                order.status == OrderStatus.CANCELLED
                or payment.status == PaymentStatus.FAILED
            ):
                payment.external_id = external_transaction_id
                payment.transition_to(PaymentStatus.REFUNDED)
                await self.uow.payments.update(payment)
                await self.uow.commit()
                logger.critical(
                    "Late payment webhook received for cancelled order %s (payment %s, transaction %s). "
                    "Payment marked as REFUNDED. Immediate refund to customer required!",
                    order.id,
                    payment.id,
                    external_transaction_id,
                )
                return payment

            # Idempotency check: terminal status payments cannot be modified
            if payment.status in {
                PaymentStatus.SUCCEEDED,
                PaymentStatus.FAILED,
                PaymentStatus.REFUNDED,
            }:
                return payment

            if status == "succeeded":
                if paid_amount != order.total_amount:
                    raise DomainValidationError(
                        f"Paid amount ({paid_amount}) does not match order total ({order.total_amount})"
                    )

                payment.external_id = external_transaction_id
                payment.transition_to(PaymentStatus.SUCCEEDED)
                order.transition_to(OrderStatus.PAID)

                await self.uow.payments.update(payment)
                await self.uow.orders.update(order)

            elif status == "failed":
                payment.external_id = external_transaction_id
                payment.transition_to(PaymentStatus.FAILED)
                order.transition_to(OrderStatus.CANCELLED)

                # Return reserved stock to variants
                items = await self.uow.orders.list_items(order.id)
                variant_ids = sorted(
                    [item.variant_id for item in items if item.variant_id is not None]
                )
                if variant_ids:
                    variants = await self.uow.variants.get_by_ids_for_update(
                        variant_ids
                    )
                    variant_map = {v.id: v for v in variants}
                    for item in items:
                        if item.variant_id and item.variant_id in variant_map:
                            variant = variant_map[item.variant_id]
                            variant.stock_quantity += item.quantity
                            await self.uow.variants.update(variant)

                await self.uow.payments.update(payment)
                await self.uow.orders.update(order)

            await self.uow.commit()
            return payment
