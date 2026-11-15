import json
from uuid import UUID

from redis.asyncio import Redis, from_url

from src.core import settings
from src.domain.interfaces import EmailVerificationData


class RedisEmailVerificationStore:
    def __init__(self, client: Redis | None = None) -> None:
        self._client = client or from_url(settings.redis_url, decode_responses=True)

    async def is_cooldown_active(self, user_id: UUID) -> bool:
        res = await self._client.exists(f"email_verify_cooldown:{user_id}")
        return bool(res > 0)

    async def set_cooldown(self, user_id: UUID, ttl_seconds: int = 60) -> None:
        await self._client.set(
            f"email_verify_cooldown:{user_id}", "1", ex=max(int(ttl_seconds), 1)
        )

    async def save_code(self, user_id: UUID, code: str, ttl_seconds: int = 600) -> None:
        payload = json.dumps({"code": code, "attempts": 0})
        await self._client.set(
            f"email_verify:{user_id}", payload, ex=max(int(ttl_seconds), 1)
        )

    async def get_code_data(self, user_id: UUID) -> EmailVerificationData | None:
        raw = await self._client.get(f"email_verify:{user_id}")
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return EmailVerificationData(
                code=data["code"], attempts=int(data.get("attempts", 0))
            )
        except Exception:
            return None

    async def increment_attempts(self, user_id: UUID) -> int:
        key = f"email_verify:{user_id}"
        raw = await self._client.get(key)
        ttl = await self._client.ttl(key)
        if not raw or ttl <= 0:
            return 5
        try:
            data = json.loads(raw)
            attempts = int(data.get("attempts", 0)) + 1
            data["attempts"] = attempts
            await self._client.set(key, json.dumps(data), ex=max(ttl, 1))
            return attempts
        except Exception:
            return 5

    async def delete_code(self, user_id: UUID) -> None:
        await self._client.delete(f"email_verify:{user_id}")

    async def aclose(self) -> None:
        await self._client.aclose()
