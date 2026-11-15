import json
from typing import Any

from redis.asyncio import Redis, from_url

from src.core import settings


class RedisEmailVerificationStore:
    def __init__(self, client: Redis | None = None) -> None:
        self._client = client or from_url(settings.redis_url, decode_responses=True)

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()

    async def save_session(
        self, token: str, payload: dict[str, Any], ttl_seconds: int = 600
    ) -> None:
        key = f"email_verify_session:{token}"
        data = json.dumps(payload)
        await self._client.set(key, data, ex=max(int(ttl_seconds), 1))

    async def get_session(self, token: str) -> dict[str, Any] | None:
        key = f"email_verify_session:{token}"
        raw = await self._client.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    async def increment_attempts(self, token: str) -> int:
        key = f"email_verify_session:{token}"
        raw = await self._client.get(key)
        ttl = await self._client.ttl(key)
        if not raw or ttl <= 0:
            return 5
        try:
            payload = json.loads(raw)
            attempts = int(payload.get("attempts", 0)) + 1
            payload["attempts"] = attempts
            if attempts >= 5:
                await self._client.delete(key)
                return attempts
            await self._client.set(key, json.dumps(payload), ex=max(ttl, 1))
            return attempts
        except Exception:
            await self._client.delete(key)
            return 5

    async def delete_session(self, token: str) -> None:
        key = f"email_verify_session:{token}"
        await self._client.delete(key)

    async def check_and_set_cooldown(self, email: str, ttl_seconds: int = 60) -> bool:
        clean_email = self._normalize_email(email)
        key = f"email_cooldown:{clean_email}"
        res = await self._client.set(key, "1", ex=max(int(ttl_seconds), 1), nx=True)
        return bool(res)

    async def aclose(self) -> None:
        await self._client.aclose()
