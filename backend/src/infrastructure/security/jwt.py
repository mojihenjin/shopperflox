from datetime import timedelta
from typing import Any
from uuid import UUID

import jwt

from src.domain.exceptions import AuthenticationError
from src.utils import factory_now


class JwtTokenProvider:
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_ttl_minutes: int = 15,
        refresh_ttl_days: int = 30,
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_ttl_minutes = access_ttl_minutes
        self.refresh_ttl_days = refresh_ttl_days

    def create_access_token(self, user_id: UUID, permissions: list[str]) -> str:
        now = factory_now()
        expire = now + timedelta(minutes=self.access_ttl_minutes)
        payload = {
            "sub": str(user_id),
            "permissions": permissions,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: UUID) -> str:
        now = factory_now()
        expire = now + timedelta(days=self.refresh_ttl_days)
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(
        self, token: str, expected_type: str | None = "access"
    ) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Invalid or expired token") from exc

        if expected_type is not None and payload.get("type") != expected_type:
            raise AuthenticationError("Invalid or expired token")

        return payload
