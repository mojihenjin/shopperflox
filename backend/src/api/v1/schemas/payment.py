from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.models import PaymentStatus


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    provider: str
    amount: Decimal
    external_id: str | None = None
    status: PaymentStatus
    paid_at: datetime | None = None


class PaymentWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    order_id: UUID
    external_transaction_id: str = Field(min_length=1, max_length=255)
    status: Literal["succeeded", "failed"]
    paid_amount: Decimal = Field(ge=0)
