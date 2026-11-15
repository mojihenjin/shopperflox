import asyncio

from fastapi import APIRouter, Depends, Response
from loguru import logger
from sqlalchemy import text

from src.core import BaseResponse, ResponseGenerator
from src.infrastructure.db import engine

router = APIRouter(prefix="/health")


async def check_postgres() -> bool:
    try:
        async with asyncio.timeout(5.0):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("PostgreSQL readiness check failed: {exc}", exc=exc)
        return False


@router.get("/", response_model=BaseResponse[dict[str, bool]], include_in_schema=False)
@router.get(
    "/ready", response_model=BaseResponse[dict[str, bool]], include_in_schema=False
)
async def ready_service(
    resp: Response,
    postgres_ready: bool | None = Depends(check_postgres),
):
    if not isinstance(postgres_ready, bool):
        postgres_ready = await check_postgres()

    services: dict[str, bool] = {
        "API": True,
        "postgres": postgres_ready,
    }

    is_ready: bool = all(services.values())
    resp.status_code = 200 if is_ready else 503
    return ResponseGenerator.answer(body=services, status_code=resp.status_code)


@router.get("/live", include_in_schema=False)
async def live_service():
    return "I'm alive!"
