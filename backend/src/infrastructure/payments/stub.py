from decimal import Decimal
from uuid import UUID

from uuid6 import uuid7

from src.domain.interfaces import PaymentSessionResult


class StubPaymentGateway:
    async def create_payment(
        self,
        *,
        order_id: UUID,
        amount: Decimal,
        currency: str = "RUB",
        description: str = "",
    ) -> PaymentSessionResult:
        external_id = f"stub_{uuid7()}"
        confirmation_url = f"/mock-checkout/{order_id}"
        return PaymentSessionResult(
            external_transaction_id=external_id,
            confirmation_url=confirmation_url,
        )
