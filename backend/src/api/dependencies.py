from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.services import (
    AuthService,
    CartService,
    CatalogService,
    FavoriteService,
    OrderService,
    PaymentService,
    ReviewService,
    UserModerationService,
    UserService,
)
from src.core import settings
from src.domain.exceptions import AuthenticationError, PermissionDeniedError
from src.domain.interfaces import (
    CartUnitOfWorkProtocol,
    CatalogUnitOfWorkProtocol,
    OrderUnitOfWorkProtocol,
    PasswordHasherProtocol,
    ReviewUnitOfWorkProtocol,
    TokenBlacklistProtocol,
    TokenProviderProtocol,
    UserUnitOfWorkProtocol,
)
from src.domain.models import UserDomain
from src.infrastructure.db import (
    SqlAlchemyCartUnitOfWork,
    SqlAlchemyCatalogUnitOfWork,
    SqlAlchemyOrderUnitOfWork,
    SqlAlchemyReviewUnitOfWork,
    SqlAlchemyUserUnitOfWork,
    async_session_maker,
)
from src.infrastructure.redis import RedisTokenBlacklist
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


def get_token_blacklist(request: Request) -> TokenBlacklistProtocol:
    blacklist = getattr(request.app.state, "token_blacklist", None)
    if blacklist is None:
        blacklist = RedisTokenBlacklist()
        request.app.state.token_blacklist = blacklist
    return blacklist


def get_auth_service(
    uow: UserUnitOfWorkProtocol = Depends(get_user_uow),
    hasher: PasswordHasherProtocol = Depends(get_password_hasher),
    token_provider: TokenProviderProtocol = Depends(get_token_provider),
    blacklist: TokenBlacklistProtocol = Depends(get_token_blacklist),
) -> AuthService:
    return AuthService(
        uow=uow,
        hasher=hasher,
        token_provider=token_provider,
        blacklist=blacklist,
    )


def get_user_service(
    uow: UserUnitOfWorkProtocol = Depends(get_user_uow),
) -> UserService:
    return UserService(uow=uow)


def get_moderation_service(
    uow: UserUnitOfWorkProtocol = Depends(get_user_uow),
) -> UserModerationService:
    return UserModerationService(uow=uow)


def get_catalog_uow(request: Request) -> CatalogUnitOfWorkProtocol:
    factory = getattr(request.app.state, "async_session_factory", async_session_maker)
    return SqlAlchemyCatalogUnitOfWork(session_factory=factory)


def get_catalog_service(
    uow: CatalogUnitOfWorkProtocol = Depends(get_catalog_uow),
) -> CatalogService:
    return CatalogService(uow=uow)


def get_favorite_service(
    uow: CatalogUnitOfWorkProtocol = Depends(get_catalog_uow),
) -> FavoriteService:
    return FavoriteService(uow=uow)


def get_cart_uow(request: Request) -> CartUnitOfWorkProtocol:
    factory = getattr(request.app.state, "async_session_factory", async_session_maker)
    return SqlAlchemyCartUnitOfWork(session_factory=factory)


def get_cart_service(
    uow: CartUnitOfWorkProtocol = Depends(get_cart_uow),
) -> CartService:
    return CartService(uow=uow)


def get_order_uow(request: Request) -> OrderUnitOfWorkProtocol:
    factory = getattr(request.app.state, "async_session_factory", async_session_maker)
    return SqlAlchemyOrderUnitOfWork(session_factory=factory)


def get_order_service(
    uow: OrderUnitOfWorkProtocol = Depends(get_order_uow),
) -> OrderService:
    return OrderService(uow=uow)


def get_payment_service(
    uow: OrderUnitOfWorkProtocol = Depends(get_order_uow),
) -> PaymentService:
    return PaymentService(uow=uow, webhook_secret=settings.webhook_secret)


def get_review_uow(request: Request) -> ReviewUnitOfWorkProtocol:
    factory = getattr(request.app.state, "async_session_factory", async_session_maker)
    return SqlAlchemyReviewUnitOfWork(session_factory=factory)


def get_review_service(
    uow: ReviewUnitOfWorkProtocol = Depends(get_review_uow),
) -> ReviewService:
    return ReviewService(uow=uow)


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
