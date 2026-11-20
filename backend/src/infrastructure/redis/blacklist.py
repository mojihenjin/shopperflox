from uuid import UUID

from redis.asyncio import Redis, from_url

from src.core import settings
from src.utils import factory_now


class RedisTokenBlacklist:
    def __init__(self, client: Redis | None = None) -> None:
        self._client = client or from_url(settings.redis_url, decode_responses=True)

    async def is_revoked(self, jti: str) -> bool:
        res = await self._client.exists(f"blacklist:{jti}")
        return bool(res > 0)

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        await self._client.set(f"blacklist:{jti}", "1", ex=max(int(ttl_seconds), 1))

    async def revoke_user(self, user_id: UUID, ttl_seconds: int = 2592000) -> None:
        await self._client.set(
            f"blacklist:user:{user_id}",
            str(factory_now().timestamp()),
            ex=max(int(ttl_seconds), 1),
        )

    async def is_user_revoked(
        self, user_id: UUID, token_iat: float | None = None
    ) -> bool:
        val = await self._client.get(f"blacklist:user:{user_id}")
        if not val:
            return False
        if token_iat is None:
            return True
        return float(val) >= float(token_iat)

    async def aclose(self) -> None:
        await self._client.aclose()
