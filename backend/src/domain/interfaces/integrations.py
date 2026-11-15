from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(slots=True, frozen=True)
class PaymentSessionResult:
    external_transaction_id: str
    confirmation_url: str


@dataclass(slots=True, frozen=True)
class EmailVerificationData:
    code: str
    attempts: int = 0


class EmailVerificationStoreProtocol(Protocol):
    async def is_cooldown_active(self, user_id: UUID) -> bool: ...

    async def set_cooldown(self, user_id: UUID, ttl_seconds: int = 60) -> None: ...

    async def save_code(
        self, user_id: UUID, code: str, ttl_seconds: int = 600
    ) -> None: ...

    async def get_code_data(self, user_id: UUID) -> EmailVerificationData | None: ...

    async def increment_attempts(self, user_id: UUID) -> int: ...

    async def delete_code(self, user_id: UUID) -> None: ...


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
