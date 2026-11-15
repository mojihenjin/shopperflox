import asyncio
import hashlib
import hmac

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from src.core import settings


class Argon2PasswordHasher:
    def __init__(
        self,
        hasher: PasswordHash | None = None,
        pepper: str | None = None,
    ) -> None:
        self._hasher = hasher or PasswordHash((Argon2Hasher(),))
        self.pepper = pepper if pepper is not None else settings.pepper
        prepared_dummy = self._prepare_password("dummy-timing-protection")
        self._dummy_hash = self._hasher.hash(prepared_dummy)

    def _prepare_password(self, plain_password: str) -> str:
        if not self.pepper:
            return plain_password
        return hmac.new(
            self.pepper.encode("utf-8"),
            plain_password.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def hash(self, password: str) -> str:
        prepared = self._prepare_password(password)
        return self._hasher.hash(prepared)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        try:
            prepared = self._prepare_password(plain_password)
            return self._hasher.verify(prepared, hashed_password)
        except Exception:
            return False

    async def verify_dummy(self, plain_password: str) -> None:
        await asyncio.to_thread(self.verify, plain_password, self._dummy_hash)
