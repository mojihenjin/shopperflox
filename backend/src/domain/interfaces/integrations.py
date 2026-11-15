from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID


@dataclass(slots=True, frozen=True)
class PaymentSessionResult:
    external_transaction_id: str
    confirmation_url: str


class EmailVerificationStoreProtocol(Protocol):
    async def save_session(
        self, token: str, payload: dict[str, Any], ttl_seconds: int = 600
    ) -> None: ...

    async def get_session(self, token: str) -> dict[str, Any] | None: ...

    async def increment_attempts(self, token: str) -> int: ...

    async def delete_session(self, token: str) -> None: ...

    async def check_and_set_cooldown(
        self, email: str, ttl_seconds: int = 60
    ) -> bool: ...


class EmailTransportProtocol(Protocol):
    async def send_email(self, to_email: str, subject: str, body_text: str) -> None: ...


class TaskQueueProtocol(Protocol):
    async def enqueue_email(
        self, to_email: str, subject: str, body_text: str
    ) -> None: ...


class FileStorageProtocol(Protocol):
    async def upload_file(self, *, key: str, data: bytes, content_type: str) -> str: ...

    async def delete_file(self, *, key: str) -> None: ...


class PaymentGatewayProtocol(Protocol):
    async def create_payment(
        self,
        *,
        order_id: UUID,
        amount: Decimal,
        currency: str = "RUB",
        description: str = "",
    ) -> PaymentSessionResult: ...
