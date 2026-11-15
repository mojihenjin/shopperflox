from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.services import AuthService, UserModerationService, UserService
from src.domain.exceptions import AuthenticationError, PermissionDeniedError
from src.domain.interfaces import (
    PasswordHasherProtocol,
    TokenProviderProtocol,
    UserUnitOfWorkProtocol,
)
from src.domain.models import UserDomain
from src.infrastructure.db import SqlAlchemyUserUnitOfWork, async_session_maker
from src.infrastructure.security import Argon2PasswordHasher, JwtTokenProvider

bearer_scheme = HTTPBearer(auto_error=False)


def get_user_uow(request: Request) -> UserUnitOfWorkProtocol:
    factory = getattr(request.app.state, "async_session_factory", async_session_maker)
    return SqlAlchemyUserUnitOfWork(session_factory=factory)


def get_password_hasher(request: Request) -> PasswordHasherProtocol:
    hasher = getattr(request.app.state, "password_hasher", None)
    if hasher is None:
        hasher = Argon2PasswordHasher()
        request.app.state.password_hasher = hasher
    return hasher


def get_token_provider(request: Request) -> TokenProviderProtocol:
    provider = getattr(request.app.state, "token_provider", None)
    if provider is None:
        provider = JwtTokenProvider()
        request.app.state.token_provider = provider
    return provider


def get_auth_service(
    uow: UserUnitOfWorkProtocol = Depends(get_user_uow),
    hasher: PasswordHasherProtocol = Depends(get_password_hasher),
    token_provider: TokenProviderProtocol = Depends(get_token_provider),
) -> AuthService:
    return AuthService(uow=uow, hasher=hasher, token_provider=token_provider)


def get_user_service(
    uow: UserUnitOfWorkProtocol = Depends(get_user_uow),
) -> UserService:
    return UserService(uow=uow)


def get_moderation_service(
    uow: UserUnitOfWorkProtocol = Depends(get_user_uow),
) -> UserModerationService:
    return UserModerationService(uow=uow)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
    token_provider: TokenProviderProtocol = Depends(get_token_provider),
) -> UserDomain:
    if not credentials or not credentials.credentials:
        raise AuthenticationError("Missing bearer token")

    payload = token_provider.decode_token(
        credentials.credentials, expected_type="access"
    )
    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise AuthenticationError("Invalid token payload: missing sub")

    try:
        user_id = UUID(str(user_id_raw))
    except (ValueError, TypeError) as exc:
        raise AuthenticationError(f"Invalid token user id: {exc}") from exc

    return await auth_service.verify_access(user_id=user_id)


def require_permission(permission: str):
    async def permission_dependency(
        current_user: UserDomain = Depends(get_current_user),
    ) -> UserDomain:
        has_perm = (
            permission in current_user.global_permissions
            or "*" in current_user.global_permissions
        )
        if not has_perm:
            raise PermissionDeniedError(f"Missing required permission: '{permission}'")
        return current_user

    return permission_dependency
