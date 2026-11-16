from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from src.api.dependencies import (
    get_brand_service,
    get_current_user,
    get_optional_current_user,
    require_permission,
)
from src.api.v1.schemas import (
    AddBrandMemberRequest,
    BrandCreateRequest,
    BrandMemberResponse,
    BrandResponse,
    BrandUpdateRequest,
    BrandVerifyRequest,
    MyBrandResponse,
    RemoveMemberResponse,
)
from src.application.services import BrandService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import BrandMemberRole, UserDomain

router = APIRouter(prefix="/brands", tags=["Brands"])


@router.get(
    "",
    response_model=BaseResponse[list[BrandResponse]],
)
async def list_active_brands(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    brand_service: BrandService = Depends(get_brand_service),
):
    brands = await brand_service.list_active_brands(limit=limit, offset=offset)
    return ResponseGenerator.answer(
        body=[BrandResponse.model_validate(b) for b in brands]
    )


@router.get(
    "/my",
    response_model=BaseResponse[list[MyBrandResponse]],
)
async def list_my_brands(
    current_user: UserDomain = Depends(get_current_user),
    brand_service: BrandService = Depends(get_brand_service),
):
    my_brands = await brand_service.list_my_brands(actor=current_user)
    return ResponseGenerator.answer(
        body=[
            MyBrandResponse(
                brand=BrandResponse.model_validate(b),
                role=role.value,
            )
            for b, role in my_brands
        ]
    )


@router.get(
    "/{slug}",
    response_model=BaseResponse[BrandResponse],
)
async def get_brand_by_slug(
    slug: str,
    current_user: UserDomain | None = Depends(get_optional_current_user),
    brand_service: BrandService = Depends(get_brand_service),
):
    brand = await brand_service.get_brand(slug=slug, actor=current_user)
    return ResponseGenerator.answer(body=BrandResponse.model_validate(brand))


@router.patch(
    "/{brand_id}/verify",
    response_model=BaseResponse[BrandResponse],
)
async def verify_brand(
    brand_id: UUID,
    req: BrandVerifyRequest,
    moderator: UserDomain = Depends(require_permission("mod:approve_manager")),
    brand_service: BrandService = Depends(get_brand_service),
):
    brand = await brand_service.verify_brand(
        actor=moderator,
        brand_id=brand_id,
        is_verified=req.is_verified,
    )
    return ResponseGenerator.answer(body=BrandResponse.model_validate(brand))


@router.post(
    "",
    response_model=BaseResponse[BrandResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_brand(
    req: BrandCreateRequest,
    current_user: UserDomain = Depends(get_current_user),
    brand_service: BrandService = Depends(get_brand_service),
):
    brand = await brand_service.create_brand(
        actor=current_user,
        name=req.name,
        his_url=req.his_url,
    )
    return ResponseGenerator.answer(
        body=BrandResponse.model_validate(brand),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/{brand_id}",
    response_model=BaseResponse[BrandResponse],
)
async def update_brand(
    brand_id: UUID,
    req: BrandUpdateRequest,
    current_user: UserDomain = Depends(get_current_user),
    brand_service: BrandService = Depends(get_brand_service),
):
    brand = await brand_service.update_brand(
        actor=current_user,
        brand_id=brand_id,
        name=req.name,
        his_url=req.his_url if "his_url" in req.model_fields_set else ...,
    )
    return ResponseGenerator.answer(body=BrandResponse.model_validate(brand))


@router.post(
    "/{brand_id}/logo",
    response_model=BaseResponse[BrandResponse],
)
async def upload_brand_logo(
    brand_id: UUID,
    file: UploadFile = File(...),
    current_user: UserDomain = Depends(get_current_user),
    brand_service: BrandService = Depends(get_brand_service),
):
    file_data = await file.read()
    brand = await brand_service.upload_brand_logo(
        actor=current_user,
        brand_id=brand_id,
        file_data=file_data,
    )
    return ResponseGenerator.answer(body=BrandResponse.model_validate(brand))


@router.delete(
    "/{brand_id}",
    response_model=BaseResponse[BrandResponse],
)
async def delete_brand(
    brand_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    brand_service: BrandService = Depends(get_brand_service),
):
    brand = await brand_service.delete_brand(
        actor=current_user,
        brand_id=brand_id,
    )
    return ResponseGenerator.answer(body=BrandResponse.model_validate(brand))


@router.get(
    "/{brand_id}/members",
    response_model=BaseResponse[list[BrandMemberResponse]],
)
async def list_brand_members(
    brand_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    brand_service: BrandService = Depends(get_brand_service),
):
    members = await brand_service.list_members(
        actor=current_user,
        brand_id=brand_id,
    )
    return ResponseGenerator.answer(
        body=[
            BrandMemberResponse(
                brand_id=m.brand_id,
                user_id=m.user_id,
                user_login=m.user_login,
                role=m.role.value,
                created_at=m.created_at,
            )
            for m in members
        ]
    )


@router.post(
    "/{brand_id}/members",
    response_model=BaseResponse[BrandMemberResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_or_update_brand_member(
    brand_id: UUID,
    req: AddBrandMemberRequest,
    current_user: UserDomain = Depends(get_current_user),
    brand_service: BrandService = Depends(get_brand_service),
):
    member = await brand_service.add_or_update_member(
        actor=current_user,
        brand_id=brand_id,
        login=req.login,
        role=BrandMemberRole(req.role),
    )
    return ResponseGenerator.answer(
        body=BrandMemberResponse(
            brand_id=member.brand_id,
            user_id=member.user_id,
            user_login=member.user_login,
            role=member.role.value,
            created_at=member.created_at,
        ),
        status_code=status.HTTP_201_CREATED,
    )


@router.delete(
    "/{brand_id}/members/{user_id}",
    response_model=BaseResponse[RemoveMemberResponse],
)
async def remove_brand_member(
    brand_id: UUID,
    user_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    brand_service: BrandService = Depends(get_brand_service),
):
    removed, brand_deleted = await brand_service.remove_member(
        actor=current_user,
        brand_id=brand_id,
        target_user_id=user_id,
    )
    return ResponseGenerator.answer(
        body=RemoveMemberResponse(
            removed=removed,
            brand_deleted=brand_deleted,
        )
    )
