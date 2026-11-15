from redis.asyncio import Redis, from_url

from src.core import settings


class RedisTokenBlacklist:
    def __init__(self, client: Redis | None = None) -> None:
        self._client = client or from_url(settings.redis_url, decode_responses=True)

    async def is_revoked(self, jti: str) -> bool:
        res = await self._client.exists(f"blacklist:{jti}")
        return bool(res > 0)

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        await self._client.set(f"blacklist:{jti}", "1", ex=max(int(ttl_seconds), 1))

    async def aclose(self) -> None:
        await self._client.aclose()
