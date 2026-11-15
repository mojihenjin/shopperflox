import asyncio
import hmac
import secrets
from uuid import UUID

from src.domain.exceptions import (
    AuthenticationError,
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from src.domain.interfaces import (
    EmailVerificationStoreProtocol,
    PasswordHasherProtocol,
    TaskQueueProtocol,
    TokenBlacklistProtocol,
    TokenProviderProtocol,
    UserUnitOfWorkProtocol,
)
from src.domain.models import RegisterResultDomain, UserDomain, UserPersonalDomain
from src.utils import factory_now


class AuthService:
    def __init__(
        self,
        uow: UserUnitOfWorkProtocol,
        hasher: PasswordHasherProtocol,
        token_provider: TokenProviderProtocol,
        blacklist: TokenBlacklistProtocol | None = None,
        verification_store: EmailVerificationStoreProtocol | None = None,
        task_queue: TaskQueueProtocol | None = None,
    ) -> None:
        self.uow = uow
        self.hasher = hasher
        self.token_provider = token_provider
        self.blacklist = blacklist
        self.verification_store = verification_store
        self.task_queue = task_queue

    async def register(
        self,
        *,
        login: str,
        password: str,
        email: str | None = None,
        created_by: UUID | None = None,
    ) -> RegisterResultDomain:
        clean_login = login.strip()
        if not clean_login:
            raise DomainValidationError("Login cannot be empty")

        clean_email = email.strip().lower() if email else None

        if clean_email is None:
            # Scenario 1: Registration without email (immediate creation)
            async with self.uow:
                if await self.uow.users.exists_active(login=clean_login):
                    raise EntityAlreadyExistsError(
                        f"User with login '{clean_login}' already exists"
                    )

                hashed_password = self.hasher.hash(password)
                user = UserDomain(
                    login=clean_login,
                    email=None,
                    password_hash=hashed_password,
                    verified_email=False,
                    created_by=created_by,
                )
                personal = UserPersonalDomain(
                    id=user.id,
                    created_by=created_by or user.id,
                )

                await self.uow.users.add(user)
                await self.uow.personal.add(personal)
                await self.uow.commit()

            return RegisterResultDomain(
                requires_verification=False,
                verification_token=None,
                user=user,
            )

        # Scenario 2: Registration with email (requires verification code)
        async with self.uow:
            if await self.uow.users.exists_active(login=clean_login, email=clean_email):
                raise EntityAlreadyExistsError(
                    f"User with login '{clean_login}' or email '{clean_email}' already exists"
                )

        if self.verification_store:
            is_allowed = await self.verification_store.check_and_set_cooldown(
                clean_email, ttl_seconds=60
            )
            if not is_allowed:
                raise DomainValidationError(
                    "Verification code request cooldown is active"
                )

        # Immediately hash password (raw password is NEVER stored in Redis)
        hashed_password = self.hasher.hash(password)

        code_val = secrets.randbelow(1_000_000)
        code_str = f"{code_val // 1000:03d}-{code_val % 1000:03d}"

        if self.task_queue:
            await self.task_queue.enqueue_email(
                clean_email,
                "Код подтверждения ShopperFlox",
                code_str,
            )

        token = secrets.token_urlsafe(32)
        payload = {
            "flow": "register",
            "login": clean_login,
            "password_hash": hashed_password,
            "email": clean_email,
            "code": code_str,
            "attempts": 0,
        }
        if self.verification_store:
            await self.verification_store.save_session(token, payload, ttl_seconds=600)

        return RegisterResultDomain(
            requires_verification=True,
            verification_token=token,
            user=None,
        )

    async def login(
        self,
        *,
        identifier: str,
        password: str,
    ) -> tuple[UserDomain, str, str]:
        clean_id = identifier.strip()

        async with self.uow:
            if "@" in clean_id:
                user = await self.uow.users.get_by_email(clean_id.lower())
            else:
                user = await self.uow.users.get_by_login(clean_id)

            if user is None or user.password_hash is None:
                await self.hasher.verify_dummy(password)
                raise AuthenticationError("Invalid credentials")

            is_valid = await asyncio.to_thread(
                self.hasher.verify, password, user.password_hash
            )
            if not is_valid:
                raise AuthenticationError("Invalid credentials")

            ban = await self.uow.bans.get_active_by_user_id(user.id)
            if ban and ban.is_active():
                raise PermissionDeniedError(f"User is banned: {ban.reason}")

            access_token = self.token_provider.create_access_token(
                user.id, user.global_permissions
            )
            refresh_token = self.token_provider.create_refresh_token(user.id)

            return user, access_token, refresh_token

    async def refresh_tokens(
        self,
        *,
        refresh_token: str,
    ) -> tuple[UserDomain, str, str]:
        payload = self.token_provider.decode_token(
            refresh_token, expected_type="refresh"
        )
        jti = payload.get("jti")
        if jti and self.blacklist and await self.blacklist.is_revoked(jti):
            raise AuthenticationError("Token has been revoked")

        user_id = UUID(payload["sub"])
        user = await self.verify_access(user_id=user_id)

        if jti and self.blacklist:
            exp = payload.get("exp", 0)
            ttl = max(int(exp - factory_now().timestamp()), 1)
            await self.blacklist.revoke(jti, ttl_seconds=ttl)

        new_access = self.token_provider.create_access_token(
            user.id, user.global_permissions
        )
        new_refresh = self.token_provider.create_refresh_token(user.id)
        return user, new_access, new_refresh

    async def logout(
        self, *, refresh_token: str, access_token: str | None = None
    ) -> None:
        payload = self.token_provider.decode_token(
            refresh_token, expected_type="refresh"
        )
        jti = payload.get("jti")
        if jti and self.blacklist:
            exp = payload.get("exp", 0)
            ttl = max(int(exp - factory_now().timestamp()), 1)
            await self.blacklist.revoke(jti, ttl_seconds=ttl)

        if access_token and self.blacklist:
            try:
                acc_payload = self.token_provider.decode_token(
                    access_token, expected_type="access"
                )
                acc_jti = acc_payload.get("jti")
                if acc_jti:
                    acc_exp = acc_payload.get("exp", 0)
                    acc_ttl = max(int(acc_exp - factory_now().timestamp()), 1)
                    await self.blacklist.revoke(acc_jti, ttl_seconds=acc_ttl)
            except Exception:
                pass

    async def verify_access(
        self,
        *,
        user_id: UUID,
        required_permission: str | None = None,
    ) -> UserDomain:
        async with self.uow:
            user = await self.uow.users.get_by_id(user_id)
            if user is None or user.is_deleted:
                raise AuthenticationError("User not found or deleted")

            ban = await self.uow.bans.get_active_by_user_id(user.id)
            if ban and ban.is_active():
                raise PermissionDeniedError(f"User is banned: {ban.reason}")

            if required_permission:
                has_perm = (
                    required_permission in user.global_permissions
                    or "*" in user.global_permissions
                )
                if not has_perm:
                    raise PermissionDeniedError(
                        f"Missing required permission: '{required_permission}'"
                    )

            return user

    async def request_bind_email_code(
        self,
        *,
        user_id: UUID,
        current_email: str | None,
        verified_email: bool,
        new_email: str,
    ) -> str:
        clean_new_email = new_email.strip().lower()
        if not clean_new_email:
            raise DomainValidationError("Email cannot be empty")

        if (
            current_email
            and current_email.strip().lower() == clean_new_email
            and verified_email
        ):
            raise DomainValidationError("Email already verified")

        async with self.uow:
            existing = await self.uow.users.get_by_email(clean_new_email)
            if existing and existing.id != user_id:
                raise EntityAlreadyExistsError(
                    f"User with email '{clean_new_email}' already exists"
                )

        if self.verification_store:
            user_allowed = await self.verification_store.check_and_set_user_cooldown(
                user_id, ttl_seconds=60
            )
            if not user_allowed:
                raise DomainValidationError(
                    "Verification code request cooldown is active for this user"
                )
            is_allowed = await self.verification_store.check_and_set_cooldown(
                clean_new_email, ttl_seconds=60
            )
            if not is_allowed:
                raise DomainValidationError(
                    "Verification code request cooldown is active"
                )

        code_val = secrets.randbelow(1_000_000)
        code_str = f"{code_val // 1000:03d}-{code_val % 1000:03d}"

        if self.task_queue:
            await self.task_queue.enqueue_email(
                clean_new_email,
                "Код подтверждения ShopperFlox",
                code_str,
            )

        token = secrets.token_urlsafe(32)
        payload = {
            "flow": "bind_email",
            "user_id": str(user_id),
            "email": clean_new_email,
            "code": code_str,
            "attempts": 0,
        }
        if self.verification_store:
            await self.verification_store.save_session(token, payload, ttl_seconds=600)

        return token

    async def confirm_verification_code(
        self,
        *,
        token: str,
        code: str,
    ) -> tuple[UserDomain, int]:
        digits = "".join(ch for ch in code if ch.isdigit())
        if len(digits) != 6:
            raise DomainValidationError("Invalid verification code format")
        normalized_code = f"{digits[:3]}-{digits[3:]}"

        if not self.verification_store:
            raise DomainValidationError("Verification session expired or invalid")

        session = await self.verification_store.get_session(token)
        if not session:
            raise DomainValidationError("Verification session expired or invalid")

        expected_code = session.get("code", "")
        if not hmac.compare_digest(expected_code, normalized_code):
            await self.verification_store.increment_attempts(token)
            raise AuthenticationError("Invalid verification code")

        await self.verification_store.delete_session(token)

        flow = session.get("flow")
        if flow == "register":
            login = session["login"]
            password_hash = session["password_hash"]
            email = session["email"]

            async with self.uow:
                if await self.uow.users.exists_active(login=login, email=email):
                    raise EntityAlreadyExistsError(
                        f"User with login '{login}' or email '{email}' already exists"
                    )

                user = UserDomain(
                    login=login,
                    email=email,
                    password_hash=password_hash,
                    verified_email=True,
                )
                personal = UserPersonalDomain(
                    id=user.id,
                    created_by=user.id,
                )

                await self.uow.users.add(user)
                await self.uow.personal.add(personal)
                try:
                    await self.uow.commit()
                except Exception as exc:
                    raise EntityAlreadyExistsError(
                        f"User with login '{login}' or email '{email}' already exists"
                    ) from exc

            return user, 201

        if flow == "bind_email":
            user_id = UUID(session["user_id"])
            email = session["email"]

            async with self.uow:
                user = await self.uow.users.get_by_id(user_id)
                if user is None or user.is_deleted:
                    raise EntityNotFoundError("User not found")

                existing = await self.uow.users.get_by_email(email)
                if existing and existing.id != user.id:
                    raise EntityAlreadyExistsError(
                        f"User with email '{email}' already exists"
                    )

                user.email = email
                user.verified_email = True
                await self.uow.users.update(user)
                await self.uow.commit()

            return user, 200

        raise DomainValidationError("Unknown verification flow")
