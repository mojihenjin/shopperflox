from fastapi import APIRouter, Response
from src.core import BaseResponse, ResponseGenerator

router = APIRouter(prefix="/health")


@router.get("/")
@router.get(
    "/ready", response_model=BaseResponse[dict[str, bool]], include_in_schema=False
)
async def ready_service(resp: Response):
    services: dict = {"API": True}

    is_ready: bool = any(services)
    resp.status_code = 200 if is_ready else 503
    return ResponseGenerator.answer(body=services, status_code=resp.status_code)


@router.get("/live", include_in_schema=False)
async def live_service():
    return "I'm alive!"
