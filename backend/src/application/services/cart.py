from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from src.domain.exceptions import DomainValidationError, EntityNotFoundError
from src.domain.interfaces import CartUnitOfWorkProtocol
from src.domain.models import (
    CartDomain,
    CartItemDomain,
    ProductDomain,
    ProductVariantDomain,
)


@dataclass(slots=True, kw_only=True)
class CartItemDetail:
    item: CartItemDomain
    variant: ProductVariantDomain | None
    product: ProductDomain | None
    unit_price: Decimal
    total_price: Decimal
    is_available: bool
    product_slug: str = ""
    image_url: str | None = None


class CartService:
    def __init__(self, uow: CartUnitOfWorkProtocol) -> None:
        self.uow = uow

    async def get_cart(
        self, user_id: UUID
    ) -> tuple[CartDomain, list[CartItemDetail], Decimal]:
        async with self.uow:
            cart = await self.uow.carts.get_or_create_for_user(user_id)
            items = await self.uow.carts.list_items(cart.id)
            details: list[CartItemDetail] = []
            total_cart_amount = Decimal("0.00")

            for item in items:
                variant = await self.uow.variants.get_by_id(item.variant_id)
                product = (
                    await self.uow.products.get_by_id(variant.product_id)
                    if variant
                    else None
                )

                if variant and product:
                    unit_price = product.resolve_price(variant)
                    is_available = (
                        product.is_available
                        and not product.brand_is_deleted
                        and variant.stock_quantity >= item.quantity
                    )
                else:
                    unit_price = Decimal("0.00")
                    is_available = False

                item_total = unit_price * item.quantity
                if is_available:
                    total_cart_amount += item_total

                product_slug = product.slug if product else ""
                image_url = None
                if product and getattr(self.uow, "images", None):
                    images = await self.uow.images.list_by_product_id(product.id)
                    variant_color = (
                        (variant.color_name or variant.color) if variant else None
                    )
                    if variant_color:
                        norm_color = variant_color.strip().lower()
                        for img in images:
                            if img.color and img.color.strip().lower() == norm_color:
                                image_url = img.url
                                break
                    if not image_url and images:
                        image_url = images[0].url

                details.append(
                    CartItemDetail(
                        item=item,
                        variant=variant,
                        product=product,
                        unit_price=unit_price,
                        total_price=item_total,
                        is_available=is_available,
                        product_slug=product_slug,
                        image_url=image_url,
                    )
                )

            return cart, details, total_cart_amount

    async def add_or_update_item(
        self, user_id: UUID, variant_id: UUID, quantity: int
    ) -> CartItemDomain | None:
        async with self.uow:
            cart = await self.uow.carts.get_or_create_for_user(user_id)

            if quantity <= 0:
                await self.uow.carts.remove_item(cart.id, variant_id)
                await self.uow.commit()
                return None

            variant = await self.uow.variants.get_by_id(variant_id)
            if variant is None:
                raise EntityNotFoundError("Product variant not found")

            product = await self.uow.products.get_by_id(variant.product_id)
            if product is None or not product.is_available:
                raise DomainValidationError("Product is not available for purchase")

            if product.brand_is_deleted:
                raise DomainValidationError("Заказ невозможен, бренд снялся с продажи")

            if quantity > variant.stock_quantity:
                raise DomainValidationError(
                    f"Requested quantity ({quantity}) exceeds available stock ({variant.stock_quantity})"
                )

            item = await self.uow.carts.upsert_item(cart.id, variant_id, quantity)
            await self.uow.commit()
            return item

    async def remove_item(self, user_id: UUID, variant_id: UUID) -> None:
        async with self.uow:
            cart = await self.uow.carts.get_by_user_id(user_id)
            if cart is not None:
                await self.uow.carts.remove_item(cart.id, variant_id)
                await self.uow.commit()

    async def clear_cart(self, user_id: UUID) -> None:
        async with self.uow:
            cart = await self.uow.carts.get_by_user_id(user_id)
            if cart is not None:
                await self.uow.carts.clear_cart(cart.id)
                await self.uow.commit()
