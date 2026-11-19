from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import (
    get_post_office_service,
    require_mail_manager_permission,
)
from src.api.v1.schemas.post_office import (
    PostOfficeCreateRequest,
    PostOfficeResponse,
    PostOfficeUpdateRequest,
)
from src.application.services.post_office import PostOfficeService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import UserDomain

router = APIRouter(prefix="/post-offices", tags=["Post Offices"])
admin_router = APIRouter(prefix="/admin/post-offices", tags=["Admin Post Offices"])


# =====================================================================
# Public Endpoints
# =====================================================================


@router.get("", response_model=BaseResponse[list[PostOfficeResponse]])
@router.get(
    "/", response_model=BaseResponse[list[PostOfficeResponse]], include_in_schema=False
)
async def list_active_post_offices(
    search: str | None = Query(default=None),
    city: str | None = Query(default=None),
    post_office_service: PostOfficeService = Depends(get_post_office_service),
):
    offices = await post_office_service.list_active(search=search, city=city)
    resp = [PostOfficeResponse.model_validate(o) for o in offices]
    return ResponseGenerator.answer(body=resp, status_code=200)


# =====================================================================
# Admin Endpoints (requires mod:mail-manager, admin:access or *)
# =====================================================================


@admin_router.get("", response_model=BaseResponse[list[PostOfficeResponse]])
@admin_router.get(
    "/", response_model=BaseResponse[list[PostOfficeResponse]], include_in_schema=False
)
async def list_all_post_offices(
    search: str | None = Query(default=None),
    city: str | None = Query(default=None),
    admin: UserDomain = Depends(require_mail_manager_permission()),
    post_office_service: PostOfficeService = Depends(get_post_office_service),
):
    offices = await post_office_service.list_all(actor=admin, search=search, city=city)
    resp = [PostOfficeResponse.model_validate(o) for o in offices]
    return ResponseGenerator.answer(body=resp, status_code=200)


@admin_router.post(
    "",
    response_model=BaseResponse[PostOfficeResponse],
    status_code=status.HTTP_201_CREATED,
)
@admin_router.post(
    "/",
    response_model=BaseResponse[PostOfficeResponse],
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_post_office(
    req: PostOfficeCreateRequest,
    admin: UserDomain = Depends(require_mail_manager_permission()),
    post_office_service: PostOfficeService = Depends(get_post_office_service),
):
    office = await post_office_service.create(
        actor=admin,
        name=req.name,
        country=req.country,
        region=req.region,
        city=req.city,
        house=req.house,
        postal_code=req.postal_code,
        note=req.note,
        is_active=req.is_active,
    )
    resp = PostOfficeResponse.model_validate(office)
    return ResponseGenerator.answer(body=resp, status_code=status.HTTP_201_CREATED)


@admin_router.patch("/{office_id}", response_model=BaseResponse[PostOfficeResponse])
async def update_post_office(
    office_id: UUID,
    req: PostOfficeUpdateRequest,
    admin: UserDomain = Depends(require_mail_manager_permission()),
    post_office_service: PostOfficeService = Depends(get_post_office_service),
):
    office = await post_office_service.update(
        actor=admin,
        office_id=office_id,
        name=req.name,
        country=req.country,
        region=req.region,
        city=req.city,
        house=req.house,
        postal_code=req.postal_code,
        note=req.note,
        is_active=req.is_active,
    )
    resp = PostOfficeResponse.model_validate(office)
    return ResponseGenerator.answer(body=resp, status_code=200)


@admin_router.delete("/{office_id}", response_model=BaseResponse[dict[str, bool]])
async def delete_post_office(
    office_id: UUID,
    admin: UserDomain = Depends(require_mail_manager_permission()),
    post_office_service: PostOfficeService = Depends(get_post_office_service),
):
    await post_office_service.delete(actor=admin, office_id=office_id)
    return ResponseGenerator.answer(body={"deleted": True}, status_code=200)
