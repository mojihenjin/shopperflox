from typing import Any, Protocol
from uuid import UUID


class PasswordHasherProtocol(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, plain_password: str, hashed_password: str) -> bool: ...

    async def verify_dummy(self, plain_password: str) -> None: ...


class TokenProviderProtocol(Protocol):
    def create_access_token(
        self,
        user_id: UUID,
        permissions: list[str] | None = None,
        *,
        login: str | None = None,
        global_permissions: list[str] | None = None,
        verified_profile: bool = False,
        verified_email: bool = False,
    ) -> str: ...

    def create_refresh_token(self, user_id: UUID) -> str: ...

    def decode_token(
        self, token: str, expected_type: str | None = "access"
    ) -> dict[str, Any]: ...


class TokenBlacklistProtocol(Protocol):
    async def is_revoked(self, jti: str) -> bool: ...

    async def revoke(self, jti: str, ttl_seconds: int) -> None: ...

    async def revoke_user(self, user_id: UUID, ttl_seconds: int = 2592000) -> None: ...

    async def is_user_revoked(
        self, user_id: UUID, token_iat: float | None = None
    ) -> bool: ...
