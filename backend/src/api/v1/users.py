from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_current_user, get_user_service
from src.api.v1.schemas import (
    CreateAddressRequest,
    UpdatePersonalRequest,
    UserAddressResponse,
    UserPersonalResponse,
    UserProfileResponse,
    UserResponse,
)
from src.application.services import UserService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import UserDomain

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=BaseResponse[UserProfileResponse])
async def get_my_profile(
    current_user: UserDomain = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    user, personal = await user_service.get_user_profile(
        actor_id=current_user.id,
        target_user_id=current_user.id,
    )
    profile = UserProfileResponse(
        user=UserResponse.model_validate(user),
        personal=UserPersonalResponse.model_validate(personal) if personal else None,
    )
    return ResponseGenerator.answer(body=profile)


@router.patch("/me/personal", response_model=BaseResponse[UserPersonalResponse])
async def update_my_personal(
    req: UpdatePersonalRequest,
    current_user: UserDomain = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    personal = await user_service.update_personal(
        actor_id=current_user.id,
        target_user_id=current_user.id,
        firstname=req.firstname,
        lastname=req.lastname,
        phone_number=req.phone_number,
    )
    return ResponseGenerator.answer(body=UserPersonalResponse.model_validate(personal))


@router.get("/me/addresses", response_model=BaseResponse[list[UserAddressResponse]])
async def list_my_addresses(
    current_user: UserDomain = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    addresses = await user_service.list_addresses(
        actor_id=current_user.id,
        target_user_id=current_user.id,
    )
    return ResponseGenerator.answer(
        body=[UserAddressResponse.model_validate(a) for a in addresses]
    )


@router.post(
    "/me/addresses",
    response_model=BaseResponse[UserAddressResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_my_address(
    req: CreateAddressRequest,
    current_user: UserDomain = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    address = await user_service.add_address(
        actor_id=current_user.id,
        target_user_id=current_user.id,
        city=req.city,
        street=req.street,
        postal_code=req.postal_code,
        is_default=req.is_default,
    )
    return ResponseGenerator.answer(
        body=UserAddressResponse.model_validate(address),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/me/addresses/{address_id}/default",
    response_model=BaseResponse[UserAddressResponse],
)
async def set_my_default_address(
    address_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    address = await user_service.set_default_address(
        actor_id=current_user.id,
        target_user_id=current_user.id,
        address_id=address_id,
    )
    return ResponseGenerator.answer(body=UserAddressResponse.model_validate(address))


@router.delete("/me/addresses/{address_id}", response_model=BaseResponse[None])
async def delete_my_address(
    address_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    await user_service.delete_address(
        actor_id=current_user.id,
        target_user_id=current_user.id,
        address_id=address_id,
    )
    return ResponseGenerator.answer(body=None, status_code=200)


@router.delete("/me", response_model=BaseResponse[None])
async def delete_my_account(
    current_user: UserDomain = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    await user_service.soft_delete_user(
        actor_id=current_user.id,
        target_user_id=current_user.id,
    )
    return ResponseGenerator.answer(body=None, status_code=200)
