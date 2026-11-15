from fastapi import APIRouter, Depends, Response, status

from src.api.dependencies import get_auth_service, get_current_user
from src.api.v1.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    SendEmailCodeRequest,
    TokenPairResponse,
    UserResponse,
    VerificationInitResponse,
    VerifyCodeRequest,
)
from src.application.services import AuthService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import UserDomain

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=BaseResponse[RegisterResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    req: RegisterRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    result = await auth_service.register(
        login=req.login,
        password=req.password,
        email=req.email,
    )
    if result.requires_verification:
        response.status_code = status.HTTP_200_OK
        return ResponseGenerator.answer(
            body=RegisterResponse(
                requires_verification=True,
                verification_token=result.verification_token,
                user=None,
            ),
            status_code=status.HTTP_200_OK,
        )

    response.status_code = status.HTTP_201_CREATED
    return ResponseGenerator.answer(
        body=RegisterResponse(
            requires_verification=False,
            verification_token=None,
            user=UserResponse.model_validate(result.user),
        ),
        status_code=status.HTTP_201_CREATED,
    )


@router.post(
    "/email/send-code",
    response_model=BaseResponse[VerificationInitResponse],
    status_code=status.HTTP_200_OK,
)
async def send_verification_code(
    req: SendEmailCodeRequest,
    current_user: UserDomain = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    token = await auth_service.request_bind_email_code(
        user_id=current_user.id,
        current_email=current_user.email,
        verified_email=current_user.verified_email,
        new_email=req.email,
    )
    return ResponseGenerator.answer(
        body=VerificationInitResponse(
            requires_verification=True,
            verification_token=token,
        ),
        status_code=status.HTTP_200_OK,
    )


@router.post(
    "/verification-code",
    response_model=BaseResponse[UserResponse],
    status_code=status.HTTP_200_OK,
)
async def verify_code(
    req: VerifyCodeRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    user, code_status = await auth_service.confirm_verification_code(
        token=req.verification_token,
        code=req.code,
    )
    response.status_code = code_status
    return ResponseGenerator.answer(
        body=UserResponse.model_validate(user),
        status_code=code_status,
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
