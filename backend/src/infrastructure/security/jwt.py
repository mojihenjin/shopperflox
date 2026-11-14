import base64
from datetime import timedelta
from typing import Any
from uuid import UUID

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from src.core import settings
from src.domain.exceptions import AuthenticationError
from src.utils import factory_now


def _load_ed25519_private_key(
    key: str | bytes | ed25519.Ed25519PrivateKey,
) -> ed25519.Ed25519PrivateKey:
    if isinstance(key, ed25519.Ed25519PrivateKey):
        return key

    if isinstance(key, str):
        raw_str = key.strip()
        if raw_str.startswith("-----BEGIN"):
            pem_bytes = raw_str.replace("\\n", "\n").encode("utf-8")
            loaded = serialization.load_pem_private_key(pem_bytes, password=None)
            if not isinstance(loaded, ed25519.Ed25519PrivateKey):
                raise ValueError("Key in PEM is not an Ed25519 private key")
            return loaded

        if len(raw_str) == 64:
            try:
                return ed25519.Ed25519PrivateKey.from_private_bytes(
                    bytes.fromhex(raw_str)
                )
            except ValueError:
                pass

        try:
            decoded = base64.b64decode(raw_str)
            if len(decoded) == 32:
                return ed25519.Ed25519PrivateKey.from_private_bytes(decoded)
        except Exception:
            pass

        if len(raw_str.encode("utf-8")) == 32:
            return ed25519.Ed25519PrivateKey.from_private_bytes(raw_str.encode("utf-8"))

    elif isinstance(key, bytes):
        if len(key) == 32:
            return ed25519.Ed25519PrivateKey.from_private_bytes(key)
        if key.startswith(b"-----BEGIN"):
            loaded = serialization.load_pem_private_key(key, password=None)
            if not isinstance(loaded, ed25519.Ed25519PrivateKey):
                raise ValueError("Key in PEM is not an Ed25519 private key")
            return loaded

    raise ValueError(
        "Unable to load Ed25519 private key. Expected 64-char hex, 32 raw bytes, or PEM string."
    )


def _load_ed25519_public_key(
    key: str | bytes | ed25519.Ed25519PublicKey,
) -> ed25519.Ed25519PublicKey:
    if isinstance(key, ed25519.Ed25519PublicKey):
        return key

    if isinstance(key, str):
        raw_str = key.strip()
        if raw_str.startswith("-----BEGIN"):
            pem_bytes = raw_str.replace("\\n", "\n").encode("utf-8")
            loaded = serialization.load_pem_public_key(pem_bytes)
            if not isinstance(loaded, ed25519.Ed25519PublicKey):
                raise ValueError("Key in PEM is not an Ed25519 public key")
            return loaded

        if len(raw_str) == 64:
            try:
                return ed25519.Ed25519PublicKey.from_public_bytes(
                    bytes.fromhex(raw_str)
                )
            except ValueError:
                pass

        try:
            decoded = base64.b64decode(raw_str)
            if len(decoded) == 32:
                return ed25519.Ed25519PublicKey.from_public_bytes(decoded)
        except Exception:
            pass

        if len(raw_str.encode("utf-8")) == 32:
            return ed25519.Ed25519PublicKey.from_public_bytes(raw_str.encode("utf-8"))

    elif isinstance(key, bytes):
        if len(key) == 32:
            return ed25519.Ed25519PublicKey.from_public_bytes(key)
        if key.startswith(b"-----BEGIN"):
            loaded = serialization.load_pem_public_key(key)
            if not isinstance(loaded, ed25519.Ed25519PublicKey):
                raise ValueError("Key in PEM is not an Ed25519 public key")
            return loaded

    raise ValueError(
        "Unable to load Ed25519 public key. Expected 64-char hex, 32 raw bytes, or PEM string."
    )


class JwtTokenProvider:
    def __init__(
        self,
        secret_key: str | None = None,
        private_key: str | bytes | ed25519.Ed25519PrivateKey | None = None,
        public_key: str | bytes | ed25519.Ed25519PublicKey | None = None,
        algorithm: str | None = None,
        access_ttl_minutes: int | None = None,
        refresh_ttl_days: int | None = None,
    ) -> None:
        self.algorithm = algorithm or settings.jwt_algorithm
        self.access_ttl_minutes = (
            access_ttl_minutes
            if access_ttl_minutes is not None
            else settings.jwt_access_ttl_minutes
        )
        self.refresh_ttl_days = (
            refresh_ttl_days
            if refresh_ttl_days is not None
            else settings.jwt_refresh_ttl_days
        )

        if self.algorithm == "EdDSA":
            if public_key is not None and private_key is None:
                # Explicitly a public-key-only verification instance
                self._private_key = None
                self._public_key = _load_ed25519_public_key(public_key)
            else:
                priv_source = private_key or secret_key or settings.jwt_private_key
                pub_source = public_key or settings.jwt_public_key

                if priv_source:
                    self._private_key: ed25519.Ed25519PrivateKey | None = (
                        _load_ed25519_private_key(priv_source)
                    )
                else:
                    self._private_key = None

                if pub_source:
                    self._public_key: ed25519.Ed25519PublicKey | None = (
                        _load_ed25519_public_key(pub_source)
                    )
                elif self._private_key is not None:
                    self._public_key = self._private_key.public_key()
                else:
                    self._private_key = ed25519.Ed25519PrivateKey.generate()
                    self._public_key = self._private_key.public_key()

            self.secret_key = ""
        else:
            sym_key = secret_key or private_key or settings.jwt_secret_key
            self.secret_key = sym_key if isinstance(sym_key, str) else str(sym_key)
            self._private_key = None
            self._public_key = None

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
        if self.algorithm == "EdDSA":
            if self._private_key is None:
                raise ValueError(
                    "Private key is required to sign JWT tokens with EdDSA"
                )
            return jwt.encode(payload, self._private_key, algorithm=self.algorithm)
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
        if self.algorithm == "EdDSA":
            if self._private_key is None:
                raise ValueError(
                    "Private key is required to sign JWT tokens with EdDSA"
                )
            return jwt.encode(payload, self._private_key, algorithm=self.algorithm)
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(
        self, token: str, expected_type: str | None = "access"
    ) -> dict[str, Any]:
        try:
            if self.algorithm == "EdDSA":
                if self._public_key is None:
                    raise ValueError(
                        "Public key is required to decode JWT tokens with EdDSA"
                    )
                payload = jwt.decode(
                    token, self._public_key, algorithms=[self.algorithm]
                )
            else:
                payload = jwt.decode(
                    token, self.secret_key, algorithms=[self.algorithm]
                )
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Invalid or expired token") from exc

        if expected_type is not None and payload.get("type") != expected_type:
            raise AuthenticationError("Invalid or expired token")

        return payload
