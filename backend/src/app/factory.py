from fastapi import FastAPI
from src.core import Settings


def create_app(settings: Settings):
    return FastAPI(title=settings.app_title, version=settings.version)


def configurate_app(app: FastAPI):
    from src.core import MetricsMiddleware

    # Add middlewares
    app.add_middleware(MetricsMiddleware)

    # Include routers
    from src.api import health, metrics

    app.include_router(health.router)
    app.include_router(metrics.router)

    return app


def get_app(settings: Settings):
    return configurate_app(app=create_app(settings=settings))
