from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_current_user, get_favorite_service
from src.api.v1.schemas import ProductResponse
from src.application.services import FavoriteService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import UserDomain

router = APIRouter(prefix="/favorites", tags=["Favorites"])


@router.get("", response_model=BaseResponse[list[ProductResponse]])
async def list_favorites(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserDomain = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service),
):
    products, total = await favorite_service.list_favorites(
        user_id=current_user.id, limit=limit, offset=offset
    )
    items = [ProductResponse.model_validate(p) for p in products]
    return ResponseGenerator.answer(
        body=items,
        metadata={"total": total, "limit": limit, "offset": offset},
    )


@router.post(
    "/{product_id}",
    response_model=BaseResponse[None],
    status_code=status.HTTP_201_CREATED,
)
async def add_favorite(
    product_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service),
):
    await favorite_service.add_favorite(user_id=current_user.id, product_id=product_id)
    return ResponseGenerator.answer(body=None, status_code=status.HTTP_201_CREATED)


@router.delete("/{product_id}", response_model=BaseResponse[None])
async def remove_favorite(
    product_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service),
):
    await favorite_service.remove_favorite(
        user_id=current_user.id, product_id=product_id
    )
    return ResponseGenerator.answer(body=None)
