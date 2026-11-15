from decimal import Decimal
from typing import Any
from uuid import UUID

from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from src.domain.interfaces import CatalogUnitOfWorkProtocol
from src.domain.models import (
    CategoryDomain,
    ProductDomain,
    ProductImageDomain,
    ProductVariantDomain,
    UserDomain,
)
from src.utils import factory_now


class CatalogService:
    def __init__(self, uow: CatalogUnitOfWorkProtocol) -> None:
        self.uow = uow

    def _check_permission(self, actor: UserDomain) -> None:
        if not actor or (
            "catalog:manage" not in actor.global_permissions
            and "*" not in actor.global_permissions
        ):
            raise PermissionDeniedError("Permission 'catalog:manage' required")

    async def get_categories(self) -> list[CategoryDomain]:
        async with self.uow:
            return await self.uow.categories.list_all()

    async def get_category_by_slug(self, slug: str) -> CategoryDomain:
        async with self.uow:
            category = await self.uow.categories.get_by_slug(slug)
            if category is None:
                raise EntityNotFoundError("Category not found")
            return category

    async def list_products(
        self,
        *,
        category_id: UUID | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductDomain], int]:
        async with self.uow:
            return await self.uow.products.list_catalog(
                category_id=category_id,
                min_price=min_price,
                max_price=max_price,
                search=search,
                limit=limit,
                offset=offset,
            )

    async def get_product_detail(
        self, slug: str
    ) -> tuple[ProductDomain, list[ProductVariantDomain], list[ProductImageDomain]]:
        async with self.uow:
            product = await self.uow.products.get_by_slug(
                slug, include_unpublished=False
            )
            if product is None or not product.is_available:
                raise EntityNotFoundError("Product not found")
            variants = await self.uow.variants.list_by_product_id(product.id)
            images = await self.uow.images.list_by_product_id(product.id)
            return product, variants, images

    async def create_category(
        self,
        *,
        actor: UserDomain,
        name: str,
        slug: str,
        parent_id: UUID | None = None,
        sort_order: int = 0,
    ) -> CategoryDomain:
        self._check_permission(actor)
        name = name.strip()
        slug = slug.strip()
        if not name or not slug:
            raise DomainValidationError("Category name and slug cannot be empty")

        async with self.uow:
            if parent_id is not None:
                parent = await self.uow.categories.get_by_id(parent_id)
                if parent is None:
                    raise EntityNotFoundError("Parent category not found")

            category = CategoryDomain(
                name=name,
                slug=slug,
                parent_id=parent_id,
                sort_order=sort_order,
                created_by=actor.id,
            )
            await self.uow.categories.add(category)
            await self.uow.commit()
            return category

    async def update_category(
        self,
        *,
        actor: UserDomain,
        category_id: UUID,
        name: str | None = None,
        slug: str | None = None,
        parent_id: UUID | None = ...,  # type: ignore[assignment]
        sort_order: int | None = None,
    ) -> CategoryDomain:
        self._check_permission(actor)
        async with self.uow:
            category = await self.uow.categories.get_by_id(category_id)
            if category is None:
                raise EntityNotFoundError("Category not found")

            if parent_id is not ...:
                if parent_id == category_id:
                    raise DomainValidationError("Category cannot be its own parent")
                if parent_id is not None:
                    curr: UUID | None = parent_id
                    visited = {category_id}
                    while curr is not None:
                        if curr in visited:
                            raise DomainValidationError(
                                "Cyclic category hierarchy detected"
                            )
                        visited.add(curr)
                        p = await self.uow.categories.get_by_id(curr)
                        if p is None:
                            raise EntityNotFoundError("Parent category not found")
                        curr = p.parent_id
                    category.parent_id = parent_id
                else:
                    category.parent_id = None

            if name is not None:
                name_clean = name.strip()
                if not name_clean:
                    raise DomainValidationError("Category name cannot be empty")
                category.name = name_clean

            if slug is not None:
                slug_clean = slug.strip()
                if not slug_clean:
                    raise DomainValidationError("Category slug cannot be empty")
                category.slug = slug_clean

            if sort_order is not None:
                category.sort_order = sort_order

            await self.uow.categories.update(category)
            await self.uow.commit()
            return category

    async def create_product(
        self,
        *,
        actor: UserDomain,
        category_id: UUID,
        title: str,
        slug: str,
        base_price: Decimal,
        description: str | None = None,
        attributes: dict[str, Any] | None = None,
        is_published: bool = False,
    ) -> ProductDomain:
        self._check_permission(actor)
        title = title.strip()
        slug = slug.strip()
        if not title or not slug:
            raise DomainValidationError("Product title and slug cannot be empty")

        async with self.uow:
            category = await self.uow.categories.get_by_id(category_id)
            if category is None:
                raise EntityNotFoundError("Category not found")

            product = ProductDomain(
                category_id=category_id,
                title=title,
                slug=slug,
                base_price=base_price,
                description=description,
                attributes=attributes or {},
                is_published=is_published,
                created_by=actor.id,
            )
            await self.uow.products.add(product)
            await self.uow.commit()
            return product

    async def update_product(
        self,
        *,
        actor: UserDomain,
        product_id: UUID,
        category_id: UUID | None = None,
        title: str | None = None,
        slug: str | None = None,
        base_price: Decimal | None = None,
        description: str | None = None,
        attributes: dict[str, Any] | None = None,
        is_published: bool | None = None,
    ) -> ProductDomain:
        self._check_permission(actor)
        async with self.uow:
            product = await self.uow.products.get_by_id(
                product_id, include_unpublished=True
            )
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            if category_id is not None:
                category = await self.uow.categories.get_by_id(category_id)
                if category is None:
                    raise EntityNotFoundError("Category not found")
                product.category_id = category_id

            if title is not None:
                title_clean = title.strip()
                if not title_clean:
                    raise DomainValidationError("Product title cannot be empty")
                product.title = title_clean

            if slug is not None:
                slug_clean = slug.strip()
                if not slug_clean:
                    raise DomainValidationError("Product slug cannot be empty")
                product.slug = slug_clean

            if base_price is not None:
                product.base_price = base_price

            if description is not None:
                product.description = description

            if attributes is not None:
                product.attributes = attributes

            if is_published is not None:
                product.is_published = is_published

            product.updated_at = factory_now()
            await self.uow.products.update(product)
            await self.uow.commit()
            return product

    async def delete_product(self, *, actor: UserDomain, product_id: UUID) -> None:
        self._check_permission(actor)
        async with self.uow:
            product = await self.uow.products.get_by_id(
                product_id, include_unpublished=True
            )
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            now = factory_now()
            product.deleted_at = now
            product.updated_at = now
            await self.uow.products.update(product)
            await self.uow.commit()

    async def create_variant(
        self,
        *,
        actor: UserDomain,
        product_id: UUID,
        sku: str,
        size: str,
        color_name: str,
        color_hex: str | None = None,
        price_override: Decimal | None = None,
        stock_quantity: int = 0,
    ) -> ProductVariantDomain:
        self._check_permission(actor)
        sku = sku.strip()
        if not sku:
            raise DomainValidationError("SKU cannot be empty")

        async with self.uow:
            product = await self.uow.products.get_by_id(
                product_id, include_unpublished=True
            )
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            variant = ProductVariantDomain(
                product_id=product_id,
                sku=sku,
                size=size,
                color_name=color_name,
                color_hex=color_hex,
                price_override=price_override,
                stock_quantity=stock_quantity,
                created_by=actor.id,
            )
            await self.uow.variants.add(variant)
            await self.uow.commit()
            return variant

    async def update_variant(
        self,
        *,
        actor: UserDomain,
        variant_id: UUID,
        sku: str | None = None,
        size: str | None = None,
        color_name: str | None = None,
        color_hex: str | None = None,
        price_override: Decimal | None = None,
        stock_quantity: int | None = None,
    ) -> ProductVariantDomain:
        self._check_permission(actor)
        async with self.uow:
            variant = await self.uow.variants.get_by_id(variant_id)
            if variant is None:
                raise EntityNotFoundError("Variant not found")

            if sku is not None:
                sku_clean = sku.strip()
                if not sku_clean:
                    raise DomainValidationError("SKU cannot be empty")
                variant.sku = sku_clean

            if size is not None:
                variant.size = size

            if color_name is not None:
                variant.color_name = color_name

            if color_hex is not None:
                variant.color_hex = color_hex

            if price_override is not None:
                variant.price_override = price_override

            if stock_quantity is not None:
                variant.stock_quantity = stock_quantity

            variant.updated_at = factory_now()
            await self.uow.variants.update(variant)
            await self.uow.commit()
            return variant

    async def add_image(
        self,
        *,
        actor: UserDomain,
        product_id: UUID,
        url: str,
        variant_id: UUID | None = None,
        alt_text: str | None = None,
        sort_order: int = 0,
        is_main: bool = False,
    ) -> ProductImageDomain:
        self._check_permission(actor)
        url = url.strip()
        if not url:
            raise DomainValidationError("Image URL cannot be empty")

        async with self.uow:
            product = await self.uow.products.get_by_id(
                product_id, include_unpublished=True
            )
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            if variant_id is not None:
                variant = await self.uow.variants.get_by_id(variant_id)
                if variant is None or variant.product_id != product_id:
                    raise EntityNotFoundError("Variant not found for this product")

            existing_images = await self.uow.images.list_by_product_id(product_id)
            should_be_main = is_main or len(existing_images) == 0

            if should_be_main:
                await self.uow.images.unset_main_for_product(product_id)

            image = ProductImageDomain(
                product_id=product_id,
                variant_id=variant_id,
                url=url,
                alt_text=alt_text,
                sort_order=sort_order,
                is_main=should_be_main,
                created_by=actor.id,
            )
            await self.uow.images.add(image)
            await self.uow.commit()
            return image
