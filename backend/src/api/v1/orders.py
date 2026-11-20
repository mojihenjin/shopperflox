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
from src.core import BaseResponse, ResponseGenerator, settings
from src.domain.models import (
    OrderDomain,
    OrderItemDomain,
    OrderStatus,
    PaymentDomain,
    UserDomain,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


def _domain_to_order_response(
    order: OrderDomain,
    items: list[OrderItemDomain] | None = None,
    payment: PaymentDomain | None = None,
) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        total_amount=order.total_amount,
        shipping_address=order.shipping_address,
        status=order.status,
        tracking_number=order.tracking_number,
        post_code=order.post_code,
        recipient_firstname=order.recipient_firstname,
        recipient_lastname=order.recipient_lastname,
        recipient_middlename=order.recipient_middlename,
        passport_series=order.passport_series,
        passport_number=order.passport_number,
        delivery_type=order.delivery_type,
        post_office_id=order.post_office_id,
        shipping_country=order.shipping_country,
        shipping_region=order.shipping_region,
        shipping_city=order.shipping_city,
        shipping_house=order.shipping_house,
        shipping_apartment=order.shipping_apartment,
        shipping_postal_code=order.shipping_postal_code,
        is_paid=order.is_paid,
        paid_at=order.paid_at,
        created_at=order.created_at,
        items=(
            [
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
            ]
            if items is not None
            else None
        ),
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
    res = await order_service.checkout(
        user_id=current_user.id,
        recipient_firstname=req.recipient_firstname,
        recipient_lastname=req.recipient_lastname,
        recipient_middlename=req.recipient_middlename,
        save_to_profile=req.save_to_profile,
        passport_series=req.passport_series if req.passport_series else None,
        passport_number=req.passport_number if req.passport_number else None,
        delivery_type=req.delivery_type,
        country=req.country,
        region=req.region,
        city=req.city,
        house=req.house,
        apartment=req.apartment,
        postal_code=req.postal_code,
        save_address_to_profile=req.save_address_to_profile,
        post_office_id=req.post_office_id,
        address_id=req.address_id,
        comment=req.comment,
    )
    order = res.order
    items = res.items
    payment = res.payment
    payment_mode = res.payment_mode
    payment_url = res.payment_url

    order_resp = _domain_to_order_response(order=order, items=items, payment=payment)
    payment_resp = (
        PaymentResponse(
            id=payment.id,
            order_id=payment.order_id,
            provider=payment.provider,
            amount=payment.amount,
            external_id=payment.external_id,
            confirmation_url=payment_url,
            status=payment.status,
            paid_at=payment.paid_at,
        )
        if payment
        else None
    )

    resp_data = OrderCheckoutResponse(
        order=order_resp,
        payment=payment_resp,
        confirmation_url=payment_url,
        payment_mode=payment_mode,
        payment_url=payment_url,
    )
    return ResponseGenerator.answer(body=resp_data, status_code=201)


@router.delete("/{order_id}/passport", response_model=BaseResponse[dict[str, bool]])
async def delete_order_passport(
    order_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    await order_service.delete_passport(actor=current_user, order_id=order_id)
    return ResponseGenerator.answer(body={"deleted": True}, status_code=200)


if settings.debug and settings.app_env != "production":
    @router.post("/{order_id}/debug-pay", response_model=BaseResponse[OrderResponse])
    async def debug_pay_order(
        order_id: UUID,
        current_user: UserDomain = Depends(get_current_user),
        order_service: OrderService = Depends(get_order_service),
    ):
        order = await order_service.debug_pay(actor=current_user, order_id=order_id)
        order_resp = _domain_to_order_response(order=order)
        return ResponseGenerator.answer(body=order_resp, status_code=200)


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

    result = [_domain_to_order_response(order=o) for o in orders]
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
    order_resp = _domain_to_order_response(order=order, items=items, payment=payment)
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
    order_resp = _domain_to_order_response(order=order)
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
    order_resp = _domain_to_order_response(order=order)
    return ResponseGenerator.answer(body=order_resp)
