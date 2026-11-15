from uuid import UUID

from src.domain.exceptions import (
    AuthenticationError,
    DomainValidationError,
    EntityAlreadyExistsError,
    PermissionDeniedError,
)
from src.domain.interfaces import (
    PasswordHasherProtocol,
    TokenBlacklistProtocol,
    TokenProviderProtocol,
    UserUnitOfWorkProtocol,
)
from src.domain.models import UserDomain, UserPersonalDomain
from src.utils import factory_now


class AuthService:
    def __init__(
        self,
        uow: UserUnitOfWorkProtocol,
        hasher: PasswordHasherProtocol,
        token_provider: TokenProviderProtocol,
        blacklist: TokenBlacklistProtocol | None = None,
    ) -> None:
        self.uow = uow
        self.hasher = hasher
        self.token_provider = token_provider
        self.blacklist = blacklist

    async def register(
        self,
        *,
        login: str,
        password: str,
        email: str | None = None,
        created_by: UUID | None = None,
    ) -> UserDomain:
        clean_login = login.strip()
        if not clean_login:
            raise DomainValidationError("Login cannot be empty")

        clean_email = email.strip().lower() if email else None

        async with self.uow:
            if await self.uow.users.exists_active(login=clean_login, email=clean_email):
                raise EntityAlreadyExistsError(
                    f"User with login '{clean_login}' or email '{clean_email}' already exists"
                )

            hashed_password = self.hasher.hash(password)
            user = UserDomain(
                login=clean_login,
                email=clean_email,
                password_hash=hashed_password,
                created_by=created_by,
            )
            personal = UserPersonalDomain(
                id=user.id,
                created_by=created_by or user.id,
            )

            await self.uow.users.add(user)
            await self.uow.personal.add(personal)
            await self.uow.commit()

        return user

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

            if not self.hasher.verify(password, user.password_hash):
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

    async def logout(self, *, refresh_token: str) -> None:
        payload = self.token_provider.decode_token(
            refresh_token, expected_type="refresh"
        )
        jti = payload.get("jti")
        if jti and self.blacklist:
            exp = payload.get("exp", 0)
            ttl = max(int(exp - factory_now().timestamp()), 1)
            await self.blacklist.revoke(jti, ttl_seconds=ttl)

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
