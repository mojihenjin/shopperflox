from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher


class Argon2PasswordHasher:
    def __init__(self, hasher: PasswordHash | None = None) -> None:
        self._hasher = hasher or PasswordHash((Argon2Hasher(),))

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return self._hasher.verify(plain_password, hashed_password)
        except Exception:
            return False
