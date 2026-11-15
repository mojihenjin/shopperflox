import json
from typing import Any
from uuid import UUID

from redis.asyncio import Redis, from_url

from src.core import settings


class RedisEmailVerificationStore:
    _INCREMENT_ATTEMPTS_LUA = """
    local key = KEYS[1]
    local raw = redis.call('GET', key)
    if not raw then
        return -1
    end
    local ttl = redis.call('TTL', key)
    if ttl <= 0 then
        redis.call('DEL', key)
        return -1
    end
    local data = cjson.decode(raw)
    local attempts = (data['attempts'] or 0) + 1
    data['attempts'] = attempts
    if attempts >= 5 then
        redis.call('DEL', key)
        return 5
    else
        redis.call('SET', key, cjson.encode(data), 'EX', ttl)
        return attempts
    end
    """

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
        res = await self._client.eval(self._INCREMENT_ATTEMPTS_LUA, 1, key)
        return int(res)

    async def delete_session(self, token: str) -> None:
        key = f"email_verify_session:{token}"
        await self._client.delete(key)

    async def check_and_set_cooldown(self, email: str, ttl_seconds: int = 60) -> bool:
        clean_email = self._normalize_email(email)
        key = f"email_cooldown:{clean_email}"
        res = await self._client.set(key, "1", ex=max(int(ttl_seconds), 1), nx=True)
        return bool(res)

    async def check_and_set_user_cooldown(
        self, user_id: UUID, ttl_seconds: int = 60
    ) -> bool:
        key = f"email_verify_user_cooldown:{user_id}"
        res = await self._client.set(key, "1", ex=max(int(ttl_seconds), 1), nx=True)
        return bool(res)

    async def aclose(self) -> None:
        await self._client.aclose()
