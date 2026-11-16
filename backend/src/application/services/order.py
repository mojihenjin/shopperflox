from decimal import Decimal
from uuid import UUID

from uuid6 import uuid7

from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from src.domain.interfaces import (
    OrderUnitOfWorkProtocol,
    PaymentGatewayProtocol,
)
from src.domain.models import (
    OrderDomain,
    OrderItemDomain,
    OrderStatus,
    PaymentDomain,
    PaymentStatus,
    UserDomain,
)

from .notification import NotificationService


class OrderService:
    def __init__(
        self,
        uow: OrderUnitOfWorkProtocol,
        payment_gateway: PaymentGatewayProtocol | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.uow = uow
        self.payment_gateway = payment_gateway
        self.notification_service = notification_service

    async def _restore_order_stock(self, order: OrderDomain) -> None:
        items = await self.uow.orders.list_items(order.id)
        variant_ids = sorted(
            [item.variant_id for item in items if item.variant_id is not None]
        )
        if variant_ids:
            variants = await self.uow.variants.get_by_ids_for_update(variant_ids)
            variant_map = {v.id: v for v in variants}
            for item in items:
                if item.variant_id and item.variant_id in variant_map:
                    variant = variant_map[item.variant_id]
                    variant.stock_quantity += item.quantity
                    await self.uow.variants.update(variant)

    async def checkout(
        self,
        user_id: UUID,
        address_id: UUID,
        comment: str | None = None,
    ) -> tuple[OrderDomain, list[OrderItemDomain], PaymentDomain, str | None]:
        # Phase 1: Short DB transaction (validate, lock SKUs, decrement stock, create pending Order & Payment, clear cart)
        async with self.uow:
            address = await self.uow.addresses.get_by_id(address_id)
            if address is None or address.user_id != user_id:
                raise EntityNotFoundError("Delivery address not found")

            shipping_snapshot = {
                "address_id": str(address.id),
                "city": address.city,
                "street": address.street,
                "postal_code": address.postal_code,
                "comment": comment,
            }

            cart = await self.uow.carts.get_by_user_id(user_id)
            if cart is None:
                raise DomainValidationError("Cart is empty")

            cart_items = await self.uow.carts.list_items(cart.id)
            if not cart_items:
                raise DomainValidationError("Cart is empty")

            variant_ids = sorted([item.variant_id for item in cart_items])
            variants = await self.uow.variants.get_by_ids_for_update(variant_ids)
            variant_map = {v.id: v for v in variants}

            order_id = uuid7()
            total_amount = Decimal("0.00")
            order_items: list[OrderItemDomain] = []

            for cart_item in cart_items:
                variant = variant_map.get(cart_item.variant_id)
                if variant is None:
                    raise DomainValidationError("Product variant no longer exists")

                product = await self.uow.products.get_by_id(variant.product_id)
                if product is None or not product.is_available:
                    raise DomainValidationError(
                        f"Product '{product.title if product else variant.sku}' is not available"
                    )

                if product.brand_is_deleted:
                    raise DomainValidationError(
                        "Заказ невозможен, бренд снялся с продажи"
                    )

                if variant.stock_quantity < cart_item.quantity:
                    raise DomainValidationError(
                        f"Insufficient stock for variant '{variant.sku}': requested {cart_item.quantity}, available {variant.stock_quantity}"
                    )

                variant.stock_quantity -= cart_item.quantity
                await self.uow.variants.update(variant)

                await self.uow.variants.increment_orders(variant.id, cart_item.quantity)
                await self.uow.products.increment_orders(product.id, cart_item.quantity)
                if product.brand_id is not None and getattr(self.uow, "brands", None):
                    await self.uow.brands.increment_orders(
                        product.brand_id, cart_item.quantity
                    )

                unit_price = product.resolve_price(variant)
                total_amount += unit_price * cart_item.quantity

                order_items.append(
                    OrderItemDomain(
                        order_id=order_id,
                        variant_id=variant.id,
                        product_slug=product.slug,
                        title_snapshot=product.title,
                        sku_snapshot=variant.sku,
                        size_snapshot=variant.size,
                        color_snapshot=variant.color_name,
                        unit_price=unit_price,
                        quantity=cart_item.quantity,
                        created_by=user_id,
                    )
                )

            order = OrderDomain(
                id=order_id,
                user_id=user_id,
                total_amount=total_amount,
                shipping_address=shipping_snapshot,
                status=OrderStatus.PENDING_PAYMENT,
                created_by=user_id,
            )

            payment = PaymentDomain(
                order_id=order_id,
                provider="stub" if self.payment_gateway else "mock",
                amount=total_amount,
                external_id=None,
                status=PaymentStatus.PENDING,
                created_by=user_id,
            )

            await self.uow.orders.add(order, order_items)
            await self.uow.payments.add(payment)
            await self.uow.carts.clear_cart(cart.id)
            await self.uow.commit()

        # Phase 2: Outside DB transaction (call payment gateway without holding DB connection / row locks)
        confirmation_url: str | None = None
        external_id: str | None = None
        gateway_error: Exception | None = None

        if self.payment_gateway:
            try:
                session_res = await self.payment_gateway.create_payment(
                    order_id=order_id,
                    amount=total_amount,
                    currency="RUB",
                    description=f"Order {order_id}",
                )
                confirmation_url = session_res.confirmation_url
                external_id = session_res.external_transaction_id
            except Exception as exc:
                gateway_error = exc

        # Phase 3: Short DB transaction (confirm payment or roll back stock and mark order cancelled)
        if gateway_error is not None:
            async with self.uow:
                restored_order = await self.uow.orders.get_by_id(
                    order_id, for_update=True
                )
                if restored_order:
                    restored_order.transition_to(OrderStatus.CANCELLED)
                    await self._restore_order_stock(restored_order)
                    await self.uow.orders.update(restored_order)

                restored_payment = await self.uow.payments.get_by_order_id(
                    order_id, for_update=True
                )
                if (
                    restored_payment
                    and restored_payment.status == PaymentStatus.PENDING
                ):
                    restored_payment.transition_to(PaymentStatus.FAILED)
                    await self.uow.payments.update(restored_payment)

                await self.uow.commit()

            raise DomainValidationError(
                f"Payment gateway failed to initialize payment: {gateway_error}"
            )

        if external_id is not None:
            async with self.uow:
                persisted_payment = await self.uow.payments.get_by_order_id(
                    order_id, for_update=True
                )
                if persisted_payment:
                    persisted_payment.external_id = external_id
                    await self.uow.payments.update(persisted_payment)
                    payment = persisted_payment
                await self.uow.commit()

        return order, order_items, payment, confirmation_url

    async def get_order(
        self, actor: UserDomain, order_id: UUID
    ) -> tuple[OrderDomain, list[OrderItemDomain], PaymentDomain | None]:
        async with self.uow:
            order = await self.uow.orders.get_by_id(order_id)
            if order is None:
                raise EntityNotFoundError("Order not found")

            is_owner = order.user_id == actor.id
            is_admin = (
                "orders:manage" in actor.global_permissions
                or "*" in actor.global_permissions
            )
            if not (is_owner or is_admin):
                raise PermissionDeniedError("Access denied to order resource")

            items = await self.uow.orders.list_items(order.id)
            payment = await self.uow.payments.get_by_order_id(order.id)
            return order, items, payment

    async def list_user_orders(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[OrderDomain], int]:
        async with self.uow:
            return await self.uow.orders.list_by_user_id(
                user_id, limit=limit, offset=offset
            )

    async def list_all_orders(
        self,
        admin: UserDomain,
        status: OrderStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[OrderDomain], int]:
        if (
            "orders:manage" not in admin.global_permissions
            and "*" not in admin.global_permissions
        ):
            raise PermissionDeniedError("Access denied")

        async with self.uow:
            return await self.uow.orders.list_all(
                status=status, limit=limit, offset=offset
            )

    async def cancel_order(self, actor: UserDomain, order_id: UUID) -> OrderDomain:
        async with self.uow:
            order = await self.uow.orders.get_by_id(order_id, for_update=True)
            if order is None:
                raise EntityNotFoundError("Order not found")

            is_owner = actor.id == order.user_id
            is_admin = (
                "orders:manage" in actor.global_permissions
                or "*" in actor.global_permissions
            )
            if not (is_owner or is_admin):
                raise PermissionDeniedError("Access denied to order resource")

            if is_owner and not is_admin:
                if order.status != OrderStatus.PENDING_PAYMENT:
                    raise DomainValidationError(
                        "Only pending orders can be cancelled by user"
                    )

            order.transition_to(OrderStatus.CANCELLED)
            await self._restore_order_stock(order)

            payment = await self.uow.payments.get_by_order_id(order.id, for_update=True)
            if payment:
                if payment.status == PaymentStatus.PENDING:
                    payment.transition_to(PaymentStatus.FAILED)
                    await self.uow.payments.update(payment)
                elif payment.status == PaymentStatus.SUCCEEDED:
                    payment.transition_to(PaymentStatus.REFUNDED)
                    await self.uow.payments.update(payment)

            await self.uow.orders.update(order)
            await self.uow.commit()

            return order

    async def update_order_status(
        self,
        admin: UserDomain,
        order_id: UUID,
        new_status: OrderStatus,
        post_code: str | None = None,
    ) -> OrderDomain:
        if (
            "orders:manage" not in admin.global_permissions
            and "*" not in admin.global_permissions
        ):
            raise PermissionDeniedError("Access denied")

        async with self.uow:
            order = await self.uow.orders.get_by_id(order_id, for_update=True)
            if order is None:
                raise EntityNotFoundError("Order not found")

            old_status = order.status
            order.transition_to(new_status)

            if post_code is not None:
                order.post_code = post_code

            if new_status == OrderStatus.CANCELLED and old_status not in {
                OrderStatus.CANCELLED,
                OrderStatus.REFUNDED,
                OrderStatus.DELIVERED,
            }:
                await self._restore_order_stock(order)
                payment = await self.uow.payments.get_by_order_id(
                    order.id, for_update=True
                )
                if payment:
                    if payment.status == PaymentStatus.PENDING:
                        payment.transition_to(PaymentStatus.FAILED)
                        await self.uow.payments.update(payment)
                    elif payment.status == PaymentStatus.SUCCEEDED:
                        payment.transition_to(PaymentStatus.REFUNDED)
                        await self.uow.payments.update(payment)

            items_to_notify: list[OrderItemDomain] = []
            should_notify = (
                new_status == OrderStatus.SHIPPED and old_status != OrderStatus.SHIPPED
            ) or (new_status == OrderStatus.SHIPPED and post_code is not None)
            if should_notify and self.notification_service is not None:
                items_to_notify = await self.uow.orders.list_items(order.id)

            await self.uow.orders.update(order)
            await self.uow.commit()

        if should_notify and self.notification_service is not None:
            if items_to_notify:
                items_summary = ", ".join(
                    f"{item.title_snapshot} (x{item.quantity})"
                    for item in items_to_notify
                )
            else:
                items_summary = "Товары"

            post_code_str = order.post_code or "Не указан"
            await self.notification_service.notify_user(
                user_id=order.user_id,
                title=f"Заказ #{str(order.id)[:8]} передан в доставку",
                body=f"В ОТПРАВКЕ: {items_summary}, {post_code_str}",
                link="/orders",
                send_email=True,
            )

        return order
