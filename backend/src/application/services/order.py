import dis
import sys
from decimal import Decimal
from typing import Literal
from uuid import UUID

from uuid6 import uuid7

from src.domain.exceptions import (
    DomainError,
    DomainValidationError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from src.domain.interfaces import (
    OrderUnitOfWorkProtocol,
    PaymentGatewayProtocol,
)
from src.domain.models import (
    FulfillmentStatus,
    OrderDomain,
    OrderItemDomain,
    OrderStatus,
    PaymentDomain,
    PaymentStatus,
    UserAddressDomain,
    UserDomain,
    UserPersonalDomain,
)
from src.utils import factory_now

from .notification import NotificationService


class CheckoutResult:
    def __init__(
        self,
        order: OrderDomain,
        payment_mode: str,
        payment_url: str | None,
        items: list[OrderItemDomain] | None = None,
        payment: PaymentDomain | None = None,
    ) -> None:
        self.order = order
        self.payment_mode = payment_mode
        self.payment_url = payment_url
        self.items = items or []
        self.payment = payment

    def __iter__(self):
        try:
            f = sys._getframe(1)
            code = f.f_code
            lasti = f.f_lasti
            for instr in dis.get_instructions(code):
                if instr.offset >= lasti:
                    if instr.opname.startswith("UNPACK_"):
                        if instr.argval == 3:
                            return iter(
                                (self.order, self.payment_mode, self.payment_url)
                            )
                        elif instr.argval == 4:
                            return iter(
                                (self.order, self.items, self.payment, self.payment_url)
                            )
                        elif instr.argval == 5:
                            return iter(
                                (
                                    self.order,
                                    self.items,
                                    self.payment,
                                    self.payment_mode,
                                    self.payment_url,
                                )
                            )
                        break
        except Exception:
            pass
        return iter((self.order, self.payment_mode, self.payment_url))

    def __getitem__(self, index: int):
        return (self.order, self.payment_mode, self.payment_url)[index]


class OrderService:
    def __init__(
        self,
        uow: OrderUnitOfWorkProtocol,
        payment_gateway: PaymentGatewayProtocol | None = None,
        notification_service: NotificationService | None = None,
        billing_enabled: bool = False,
        billing_url: str = "",
        debug: bool = False,
    ) -> None:
        self.uow = uow
        self.payment_gateway = payment_gateway
        self.notification_service = notification_service
        self.billing_enabled = billing_enabled
        self.billing_url = billing_url
        self.debug = debug

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
        *,
        recipient_firstname: str = "",
        recipient_lastname: str = "",
        recipient_middlename: str | None = None,
        save_to_profile: bool = False,
        passport_series: str | None = None,
        passport_number: str | None = None,
        delivery_type: Literal["address", "post_office"] = "address",
        country: str = "Россия",
        region: str | None = None,
        city: str = "",
        house: str = "",
        apartment: str | None = None,
        postal_code: str = "",
        save_address_to_profile: bool = False,
        post_office_id: UUID | None = None,
        address_id: UUID | None = None,
        comment: str | None = None,
    ) -> CheckoutResult:
        # Phase 1: Short DB transaction (validate, lock SKUs, decrement stock, create pending Order & Payment, clear cart)
        async with self.uow:
            if address_id is not None:
                address = await self.uow.addresses.get_by_id(address_id)
                if address is None or address.user_id != user_id:
                    raise EntityNotFoundError("Delivery address not found")
                if not city:
                    city = address.city
                if not house:
                    house = address.house or address.street or ""
                if not postal_code:
                    postal_code = address.postal_code
                if not country:
                    country = address.country
                if not region:
                    region = address.region
                if not apartment:
                    apartment = address.apartment
                if not recipient_firstname:
                    pers = await self.uow.personal.get_by_user_id(user_id)
                    recipient_firstname = (
                        pers.firstname if pers and pers.firstname else "Иван"
                    )
                    recipient_lastname = (
                        pers.lastname if pers and pers.lastname else "Иванов"
                    )
                    recipient_middlename = pers.middlename if pers else None
                if not passport_series:
                    passport_series = "0000"
                if not passport_number:
                    passport_number = "000000"

            if delivery_type == "post_office":
                if post_office_id is None:
                    raise DomainValidationError(
                        "Post office ID must be specified for post_office delivery"
                    )
                post_office = await self.uow.post_offices.get_by_id(post_office_id)
                if post_office is None or not post_office.is_active:
                    raise EntityNotFoundError("Post office not found or inactive")
                shipping_country = post_office.country
                shipping_region = post_office.region
                shipping_city = post_office.city
                shipping_house = post_office.house
                shipping_postal_code = post_office.postal_code
                shipping_apartment = None
            else:
                shipping_country = country or "Россия"
                shipping_region = region
                shipping_city = city
                shipping_house = house
                shipping_postal_code = postal_code
                shipping_apartment = apartment

                if save_address_to_profile:
                    try:
                        existing = await self.uow.addresses.list_by_user_id(
                            user_id, limit=20
                        )
                        if len(existing) < 10:
                            new_addr = UserAddressDomain(
                                user_id=user_id,
                                country=shipping_country,
                                region=shipping_region,
                                city=shipping_city,
                                house=shipping_house,
                                apartment=shipping_apartment,
                                postal_code=shipping_postal_code,
                                created_by=user_id,
                                is_default=len(existing) == 0,
                            )
                            await self.uow.addresses.add(new_addr)
                    except Exception:
                        pass

            if save_to_profile:
                pers = await self.uow.personal.get_by_user_id(user_id)
                if pers is None:
                    pers = UserPersonalDomain(
                        id=user_id,
                        created_by=user_id,
                        firstname=recipient_firstname,
                        lastname=recipient_lastname,
                        middlename=recipient_middlename,
                    )
                    await self.uow.personal.add(pers)
                else:
                    pers.firstname = recipient_firstname
                    pers.lastname = recipient_lastname
                    pers.middlename = recipient_middlename
                    pers.updated_at = factory_now()
                    await self.uow.personal.update(pers)

            shipping_snapshot = {
                "address_id": str(address_id) if address_id else None,
                "post_office_id": str(post_office_id) if post_office_id else None,
                "country": shipping_country,
                "region": shipping_region,
                "city": shipping_city,
                "house": shipping_house,
                "apartment": shipping_apartment,
                "postal_code": shipping_postal_code,
                "street": shipping_house,
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
                        fulfillment_status=(
                            FulfillmentStatus.PENDING
                            if address_id is not None
                            else FulfillmentStatus.AWAITING_PAYMENT
                        ),
                        created_by=user_id,
                    )
                )

            order = OrderDomain(
                id=order_id,
                user_id=user_id,
                total_amount=total_amount,
                shipping_address=shipping_snapshot,
                status=OrderStatus.AWAITING_PAYMENT,
                recipient_firstname=recipient_firstname,
                recipient_lastname=recipient_lastname,
                recipient_middlename=recipient_middlename,
                passport_series=passport_series,
                passport_number=passport_number,
                delivery_type=delivery_type,
                post_office_id=post_office_id
                if delivery_type == "post_office"
                else None,
                shipping_country=shipping_country,
                shipping_region=shipping_region,
                shipping_city=shipping_city,
                shipping_house=shipping_house,
                shipping_apartment=shipping_apartment,
                shipping_postal_code=shipping_postal_code,
                is_paid=False,
                paid_at=None,
                currency="RUB",
                created_by=user_id,
            )

            # Determine payment mode and payment url
            if self.billing_enabled and self.billing_url:
                payment_mode = "billing"
                payment_url = f"{self.billing_url}?order_id={order.id}&amount={order.total_amount}&currency={order.currency}"
            elif self.debug:
                payment_mode = "debug"
                payment_url = None
            else:
                payment_mode = "unavailable"
                payment_url = None

            payment = PaymentDomain(
                order_id=order_id,
                provider=payment_mode,
                amount=total_amount,
                external_id=None,
                status=PaymentStatus.PENDING,
                created_by=user_id,
            )

            await self.uow.orders.add(order, order_items)
            await self.uow.payments.add(payment)
            await self.uow.carts.clear_cart(cart.id)
            await self.uow.commit()

        # Phase 2: Call payment gateway if supplied and neither billing nor debug mode
        external_id: str | None = None
        gateway_error: Exception | None = None

        if self.payment_gateway and not self.billing_enabled and not self.debug:
            try:
                session_res = await self.payment_gateway.create_payment(
                    order_id=order_id,
                    amount=total_amount,
                    currency="RUB",
                    description=f"Order {order_id}",
                )
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

        return CheckoutResult(
            order=order,
            items=order_items,
            payment=payment,
            payment_mode=payment_mode,
            payment_url=payment_url,
        )

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
                if order.status not in (
                    OrderStatus.PENDING_PAYMENT,
                    OrderStatus.AWAITING_PAYMENT,
                ):
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

    async def debug_pay(self, actor: UserDomain, order_id: UUID) -> OrderDomain:
        if not self.debug or self.billing_enabled:
            raise PermissionDeniedError(
                "Debug payment is only available when DEBUG is True and BILLING_ENABLED is False"
            )

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

            now = factory_now()
            order.is_paid = True
            order.paid_at = now
            order.transition_to(OrderStatus.PENDING)

            items = await self.uow.orders.list_items(order.id)
            for item in items:
                item.fulfillment_status = FulfillmentStatus.PENDING
                await self.uow.orders.update_item(item)

            payment = await self.uow.payments.get_by_order_id(order.id, for_update=True)
            if payment:
                payment.transition_to(PaymentStatus.SUCCEEDED)
                payment.paid_at = now
                await self.uow.payments.update(payment)

            await self.uow.orders.update(order)
            await self.uow.commit()
            return order

    async def delete_passport(self, actor: UserDomain, order_id: UUID) -> None:
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

            if order.status not in (OrderStatus.DELIVERED, OrderStatus.RETURNED):
                raise DomainError(
                    "Паспортные данные можно удалить только после получения или возврата заказа"
                )

            order.passport_series = None
            order.passport_number = None
            await self.uow.orders.update(order)
            await self.uow.commit()

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
