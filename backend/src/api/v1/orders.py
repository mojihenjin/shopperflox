from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import (
    get_current_user,
    get_order_service,
    require_permission,
)
from src.api.v1.schemas.order import (
    CheckoutRequest,
    OrderCheckoutResponse,
    OrderItemResponse,
    OrderResponse,
    OrderStatusUpdateRequest,
)
from src.api.v1.schemas.payment import PaymentResponse
from src.application.services import OrderService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import OrderStatus, UserDomain

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "/checkout",
    response_model=BaseResponse[OrderCheckoutResponse],
    status_code=201,
)
async def checkout(
    req: CheckoutRequest,
    current_user: UserDomain = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    order, items, payment, confirmation_url = await order_service.checkout(
        user_id=current_user.id,
        address_id=req.address_id,
        comment=req.comment,
    )

    order_resp = OrderResponse(
        id=order.id,
        user_id=order.user_id,
        total_amount=order.total_amount,
        shipping_address=order.shipping_address,
        status=order.status,
        tracking_number=order.tracking_number,
        post_code=order.post_code,
        created_at=order.created_at,
        items=[
            OrderItemResponse(
                id=i.id,
                variant_id=i.variant_id,
                title_snapshot=i.title_snapshot,
                sku_snapshot=i.sku_snapshot,
                size_snapshot=i.size_snapshot,
                color_snapshot=i.color_snapshot,
                unit_price=i.unit_price,
                quantity=i.quantity,
                product_slug=i.product_slug,
            )
            for i in items
        ],
    )
    payment_resp = PaymentResponse(
        id=payment.id,
        order_id=payment.order_id,
        provider=payment.provider,
        amount=payment.amount,
        external_id=payment.external_id,
        confirmation_url=confirmation_url,
        status=payment.status,
        paid_at=payment.paid_at,
    )

    resp_data = OrderCheckoutResponse(
        order=order_resp,
        payment=payment_resp,
        confirmation_url=confirmation_url,
    )
    return ResponseGenerator.answer(body=resp_data, status_code=201)


@router.get("", response_model=BaseResponse[list[OrderResponse]])
@router.get(
    "/", response_model=BaseResponse[list[OrderResponse]], include_in_schema=False
)
async def list_orders(
    status: OrderStatus | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserDomain = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    is_admin = (
        "orders:manage" in current_user.global_permissions
        or "*" in current_user.global_permissions
    )
    if is_admin and status is not None:
        orders, total = await order_service.list_all_orders(
            admin=current_user, status=status, limit=limit, offset=offset
        )
    else:
        orders, total = await order_service.list_user_orders(
            user_id=current_user.id, limit=limit, offset=offset
        )

    result = [
        OrderResponse(
            id=o.id,
            user_id=o.user_id,
            total_amount=o.total_amount,
            shipping_address=o.shipping_address,
            status=o.status,
            tracking_number=o.tracking_number,
            post_code=o.post_code,
            created_at=o.created_at,
        )
        for o in orders
    ]
    return ResponseGenerator.answer(
        body=result,
        metadata={"total": total, "limit": limit, "offset": offset},
    )


@router.get("/{order_id}", response_model=BaseResponse[OrderResponse])
async def get_order_detail(
    order_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    order, items, payment = await order_service.get_order(
        actor=current_user,
        order_id=order_id,
    )
    order_resp = OrderResponse(
        id=order.id,
        user_id=order.user_id,
        total_amount=order.total_amount,
        shipping_address=order.shipping_address,
        status=order.status,
        tracking_number=order.tracking_number,
        post_code=order.post_code,
        created_at=order.created_at,
        items=[
            OrderItemResponse(
                id=i.id,
                variant_id=i.variant_id,
                title_snapshot=i.title_snapshot,
                sku_snapshot=i.sku_snapshot,
                size_snapshot=i.size_snapshot,
                color_snapshot=i.color_snapshot,
                unit_price=i.unit_price,
                quantity=i.quantity,
                product_slug=i.product_slug,
            )
            for i in items
        ],
        payment=(
            PaymentResponse(
                id=payment.id,
                order_id=payment.order_id,
                provider=payment.provider,
                amount=payment.amount,
                external_id=payment.external_id,
                status=payment.status,
                paid_at=payment.paid_at,
            )
            if payment
            else None
        ),
    )
    return ResponseGenerator.answer(body=order_resp)


@router.post("/{order_id}/cancel", response_model=BaseResponse[OrderResponse])
async def cancel_order(
    order_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    order = await order_service.cancel_order(
        actor=current_user,
        order_id=order_id,
    )
    order_resp = OrderResponse(
        id=order.id,
        user_id=order.user_id,
        total_amount=order.total_amount,
        shipping_address=order.shipping_address,
        status=order.status,
        tracking_number=order.tracking_number,
        post_code=order.post_code,
        created_at=order.created_at,
    )
    return ResponseGenerator.answer(body=order_resp)


@router.patch("/{order_id}/status", response_model=BaseResponse[OrderResponse])
async def update_order_status(
    order_id: UUID,
    req: OrderStatusUpdateRequest,
    current_user: UserDomain = Depends(require_permission("orders:manage")),
    order_service: OrderService = Depends(get_order_service),
):
    order = await order_service.update_order_status(
        admin=current_user,
        order_id=order_id,
        new_status=req.status,
        post_code=req.post_code,
    )
    order_resp = OrderResponse(
        id=order.id,
        user_id=order.user_id,
        total_amount=order.total_amount,
        shipping_address=order.shipping_address,
        status=order.status,
        tracking_number=order.tracking_number,
        post_code=order.post_code,
        created_at=order.created_at,
    )
    return ResponseGenerator.answer(body=order_resp)
