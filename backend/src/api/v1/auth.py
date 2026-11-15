from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_auth_service
from src.api.v1.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenPairResponse,
    UserResponse,
)
from src.application.services import AuthService
from src.core import BaseResponse, ResponseGenerator

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=BaseResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    req: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    user = await auth_service.register(
        login=req.login,
        password=req.password,
        email=req.email,
    )
    return ResponseGenerator.answer(
        body=UserResponse.model_validate(user),
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/login", response_model=BaseResponse[TokenPairResponse])
async def login(
    req: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    _, access_token, refresh_token = await auth_service.login(
        identifier=req.identifier,
        password=req.password,
    )
    return ResponseGenerator.answer(
        body=TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )


@router.post("/refresh", response_model=BaseResponse[TokenPairResponse])
async def refresh(
    req: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    _, access_token, refresh_token = await auth_service.refresh_tokens(
        refresh_token=req.refresh_token,
    )
    return ResponseGenerator.answer(
        body=TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )


@router.post("/logout", response_model=BaseResponse[None])
async def logout(
    req: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    await auth_service.logout(refresh_token=req.refresh_token)
    return ResponseGenerator.answer(body=None, status_code=200)
