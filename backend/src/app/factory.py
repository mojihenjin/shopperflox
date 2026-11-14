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
