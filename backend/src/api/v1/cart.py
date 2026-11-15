from uuid import UUID

from fastapi import APIRouter, Depends

from src.api.dependencies import get_cart_service, get_current_user
from src.api.v1.schemas.cart import CartItemRequest, CartItemResponse, CartResponse
from src.application.services import CartService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import UserDomain

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("", response_model=BaseResponse[CartResponse])
@router.get("/", response_model=BaseResponse[CartResponse], include_in_schema=False)
async def get_my_cart(
    current_user: UserDomain = Depends(get_current_user),
    cart_service: CartService = Depends(get_cart_service),
):
    cart, details, total_amount = await cart_service.get_cart(current_user.id)
    items_response = [
        CartItemResponse(
            id=d.item.id,
            variant_id=d.item.variant_id,
            quantity=d.item.quantity,
            product_id=d.variant.product_id if d.variant else None,
            title=d.product.title if d.product else None,
            sku=d.variant.sku if d.variant else None,
            size=d.variant.size if d.variant else None,
            color_name=d.variant.color_name if d.variant else None,
            unit_price=d.unit_price,
            total_price=d.total_price,
            is_available=d.is_available,
        )
        for d in details
    ]
    cart_resp = CartResponse(
        id=cart.id,
        user_id=cart.user_id,
        items=items_response,
        total_amount=total_amount,
    )
    return ResponseGenerator.answer(body=cart_resp)


@router.put("/items/{variant_id}", response_model=BaseResponse[dict[str, bool]])
async def update_cart_item(
    variant_id: UUID,
    req: CartItemRequest,
    current_user: UserDomain = Depends(get_current_user),
    cart_service: CartService = Depends(get_cart_service),
):
    await cart_service.add_or_update_item(
        user_id=current_user.id,
        variant_id=variant_id,
        quantity=req.quantity,
    )
    return ResponseGenerator.answer(body={"success": True})


@router.delete("/items/{variant_id}", response_model=BaseResponse[dict[str, bool]])
async def delete_cart_item(
    variant_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    cart_service: CartService = Depends(get_cart_service),
):
    await cart_service.remove_item(
        user_id=current_user.id,
        variant_id=variant_id,
    )
    return ResponseGenerator.answer(body={"deleted": True})


@router.delete("", response_model=BaseResponse[dict[str, bool]])
@router.delete(
    "/", response_model=BaseResponse[dict[str, bool]], include_in_schema=False
)
async def clear_my_cart(
    current_user: UserDomain = Depends(get_current_user),
    cart_service: CartService = Depends(get_cart_service),
):
    await cart_service.clear_cart(user_id=current_user.id)
    return ResponseGenerator.answer(body={"cleared": True})
