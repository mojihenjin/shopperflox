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
    task = asyncio.create_task(monitor_event_loop_lag())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def create_app(settings: Settings):
    return FastAPI(
        title=settings.app_title,
        version=settings.version,
        lifespan=lifespan,
    )


def configurate_app(app: FastAPI, settings: Settings | None = None):
    if settings is None:
        from src.core import settings as default_settings

        settings = default_settings

    # Initialize logging
    setup_logging(settings=settings)

    # Middlewares
    app.middleware("http")(add_process_time_header)
    app.add_middleware(MetricsMiddleware)

    # Exception handlers
    from src.domain.exceptions import (
        AuthenticationError,
        DomainError,
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

    app.include_router(health.router)
    app.include_router(metrics.router)

    return app


def get_app(settings: Settings):
    return configurate_app(app=create_app(settings=settings), settings=settings)
