import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core import (
    MetricsMiddleware,
    ResponseGenerator,
    Settings,
    monitor_event_loop_lag,
    setup_logging,
)
from src.middlewares import add_process_time_header


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.infrastructure.db import async_session_maker
    from src.infrastructure.redis import RedisTokenBlacklist
    from src.infrastructure.security import Argon2PasswordHasher, JwtTokenProvider

    app.state.async_session_factory = async_session_maker
    app.state.password_hasher = Argon2PasswordHasher()
    app.state.token_provider = JwtTokenProvider()
    app.state.token_blacklist = RedisTokenBlacklist()

    task = asyncio.create_task(monitor_event_loop_lag())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        if hasattr(app.state, "token_blacklist") and hasattr(
            app.state.token_blacklist, "aclose"
        ):
            with contextlib.suppress(Exception):
                await app.state.token_blacklist.aclose()


def create_app(settings: Settings):
    return FastAPI(
        title=settings.app_title,
        version=settings.version,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )


def configurate_app(app: FastAPI, settings: Settings | None = None):
    if settings is None:
        from src.core import settings as default_settings

        settings = default_settings

    # Initialize logging
    setup_logging(settings=settings)

    # Initialize state singletons fallback
    from src.infrastructure.db import async_session_maker
    from src.infrastructure.redis import RedisTokenBlacklist
    from src.infrastructure.security import Argon2PasswordHasher, JwtTokenProvider

    if not hasattr(app.state, "async_session_factory"):
        app.state.async_session_factory = async_session_maker
    if not hasattr(app.state, "password_hasher"):
        app.state.password_hasher = Argon2PasswordHasher()
    if not hasattr(app.state, "token_provider"):
        app.state.token_provider = JwtTokenProvider()
    if not hasattr(app.state, "token_blacklist"):
        app.state.token_blacklist = RedisTokenBlacklist()

    # Middlewares
    app.middleware("http")(add_process_time_header)
    app.add_middleware(MetricsMiddleware)

    # Exception handlers
    from src.domain.exceptions import (
        AuthenticationError,
        DomainError,
        DomainValidationError,
        EntityAlreadyExistsError,
        EntityNotFoundError,
        InvalidStateTransitionError,
        PermissionDeniedError,
    )

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError):
        return ResponseGenerator.json_error(
            status_code=401,
            errors=[{"detail": exc.message}],
        )

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
        return ResponseGenerator.json_error(
            status_code=403,
            errors=[{"detail": exc.message}],
        )

    @app.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundError):
        return ResponseGenerator.json_error(
            status_code=404,
            errors=[{"detail": exc.message}],
        )

    @app.exception_handler(EntityAlreadyExistsError)
    async def entity_already_exists_handler(
        request: Request, exc: EntityAlreadyExistsError
    ):
        return ResponseGenerator.json_error(
            status_code=409,
            errors=[{"detail": exc.message}],
        )

    @app.exception_handler(InvalidStateTransitionError)
    async def invalid_state_transition_handler(
        request: Request, exc: InvalidStateTransitionError
    ):
        return ResponseGenerator.json_error(
            status_code=409,
            errors=[{"detail": exc.message}],
        )

    @app.exception_handler(DomainValidationError)
    async def domain_validation_error_handler(
        request: Request, exc: DomainValidationError
    ):
        return ResponseGenerator.json_error(
            status_code=422,
            errors=[{"detail": exc.message}],
        )

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        return ResponseGenerator.json_error(
            status_code=400,
            errors=[{"detail": exc.message}],
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return ResponseGenerator.json_error(
            status_code=exc.status_code,
            errors=[{"detail": exc.detail}],
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return ResponseGenerator.json_error(
            status_code=422,
            errors=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled server exception: {exc}", exc=exc)
        return ResponseGenerator.json_error(
            status_code=500,
            errors=[{"detail": "Internal server error"}],
        )

    # Include routers
    from src.api import health, metrics
    from src.api.v1 import v1_router

    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(v1_router)

    from fastapi.responses import RedirectResponse

    @app.get("/api", include_in_schema=False)
    @app.get("/api/", include_in_schema=False)
    async def redirect_api_root():
        return RedirectResponse(url="/api/docs")

    @app.get("/docs", include_in_schema=False)
    async def redirect_legacy_docs():
        return RedirectResponse(url="/api/docs")

    return app


def get_app(settings: Settings):
    return configurate_app(app=create_app(settings=settings), settings=settings)
