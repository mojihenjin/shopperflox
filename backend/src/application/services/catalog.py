from decimal import Decimal
from typing import Any
from uuid import UUID

from uuid6 import uuid7

from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from src.domain.interfaces import (
    CatalogUnitOfWorkProtocol,
    FileStorageProtocol,
)
from src.domain.models import (
    CategoryDomain,
    ModerationRequestType,
    ModerationStatus,
    ProductDomain,
    ProductImageDomain,
    ProductVariantDomain,
    SearchResultDomain,
    UserDomain,
)
from src.utils import factory_now

from .notification import NotificationService


class CatalogService:
    def __init__(
        self,
        uow: CatalogUnitOfWorkProtocol,
        storage: FileStorageProtocol | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.uow = uow
        self.storage = storage
        self.notification_service = notification_service

    def _check_permission(self, actor: UserDomain) -> None:
        if not actor or (
            "catalog:manage" not in actor.global_permissions
            and "*" not in actor.global_permissions
        ):
            raise PermissionDeniedError("Permission 'catalog:manage' required")

    def _check_moderator_permission(self, actor: UserDomain) -> None:
        if not actor or not (
            "*" in actor.global_permissions
            or "mod:approve_manager" in actor.global_permissions
        ):
            raise PermissionDeniedError("Permission 'mod:approve_manager' required")

    def _check_creator_permission(self, actor: UserDomain) -> None:
        if not actor or not (
            "*" in actor.global_permissions
            or "catalog:manage" in actor.global_permissions
            or any(
                p.startswith("creator:") or p == "creator"
                for p in actor.global_permissions
            )
        ):
            raise PermissionDeniedError(
                "Permission 'catalog:manage' or 'creator:*' required"
            )

    async def _check_product_modify_permission(
        self, actor: UserDomain, product: ProductDomain
    ) -> None:
        if not actor:
            raise PermissionDeniedError("Authentication required")
        perms = set(actor.global_permissions)
        if bool({"*", "catalog:manage", "mod:update", "mod:delete"} & perms):
            return
        if product.creator_id is not None and product.creator_id == actor.id:
            return
        if product.brand_id is not None and getattr(self.uow, "brands", None):
            member = await self.uow.brands.get_member(product.brand_id, actor.id)
            if member is not None:
                return
        raise PermissionDeniedError(
            "Access denied: only product creator, brand members, or catalog managers can modify this product"
        )

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
        self, slug: str, *, actor: UserDomain | None = None
    ) -> tuple[ProductDomain, list[ProductVariantDomain], list[ProductImageDomain]]:
        async with self.uow:
            product = await self.uow.products.get_by_slug(
                slug, include_unpublished=False
            )
            if (
                product is None
                or product.deleted_at is not None
                or not product.is_published
            ):
                raise EntityNotFoundError("Product not found")

            if product.moderation_status != ModerationStatus.APPROVED:
                has_access = actor is not None and (
                    actor.id == product.creator_id
                    or actor.id == product.created_by
                    or bool(
                        {"*", "catalog:manage", "mod:update", "mod:approve_manager"}
                        & set(actor.global_permissions)
                    )
                )
                if not has_access:
                    raise EntityNotFoundError("Product not found")

            if product.is_hidden == 2:
                has_access = actor is not None and (
                    actor.id == product.creator_id
                    or actor.id == product.created_by
                    or bool(
                        {"*", "catalog:manage", "mod:update", "mod:approve_manager"}
                        & set(actor.global_permissions)
                    )
                )
                if not has_access:
                    raise EntityNotFoundError("Product not found")

            variants = await self.uow.variants.list_by_product_id(product.id)
            images = await self.uow.images.list_by_product_id(product.id)
            return product, variants, images

    get_product_by_slug = get_product_detail

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
        price_usd: Decimal | None = None,
        price_eur: Decimal | None = None,
        brand_id: UUID | None = None,
        brand: str | None = None,
        is_self_worked: bool = False,
        material: str | None = None,
        density: str | None = None,
        composition: str | None = None,
        print_method: str | None = None,
        note: str | None = None,
        description: str | None = None,
        attributes: dict[str, Any] | None = None,
        is_published: bool = False,
        is_hidden: int = 0,
        is_limited: bool = False,
        variants: list[dict[str, Any]] | None = None,
    ) -> ProductDomain:
        self._check_creator_permission(actor)
        title = title.strip()
        slug = slug.strip()
        clean_brand = brand.strip() if brand else None
        if not title or not slug:
            raise DomainValidationError("Product title and slug cannot be empty")

        if is_hidden not in (0, 1, 2):
            raise DomainValidationError("is_hidden must be 0, 1, or 2")

        if is_self_worked and not clean_brand:
            clean_brand = "self-worked"

        async with self.uow:
            category = await self.uow.categories.get_by_id(category_id)
            if category is None:
                raise EntityNotFoundError("Category not found")

            brand_slug = None
            brand_is_deleted = False
            if brand_id is not None and getattr(self.uow, "brands", None):
                brand_domain = await self.uow.brands.get_by_id(brand_id)
                if brand_domain is None:
                    raise EntityNotFoundError("Brand not found")
                clean_brand = brand_domain.name
                brand_slug = brand_domain.slug
                brand_is_deleted = brand_domain.is_deleted
                if "*" not in actor.global_permissions:
                    member = await self.uow.brands.get_member(brand_id, actor.id)
                    if not member:
                        raise PermissionDeniedError(
                            "Membership in brand required to create brand products"
                        )

            product = ProductDomain(
                category_id=category_id,
                creator_id=actor.id,
                brand_id=brand_id,
                title=title,
                slug=slug,
                brand=clean_brand,
                brand_slug=brand_slug,
                brand_is_deleted=brand_is_deleted,
                is_self_worked=is_self_worked,
                base_price=base_price,
                price_usd=price_usd,
                price_eur=price_eur,
                material=material.strip() if material else None,
                density=density.strip() if density else None,
                composition=composition.strip() if composition else None,
                print_method=print_method.strip() if print_method else None,
                note=note.strip() if note else None,
                description=description,
                attributes=attributes or {},
                is_published=is_published,
                is_hidden=is_hidden,
                is_limited=is_limited,
                moderation_status=ModerationStatus.PENDING,
                request_type=ModerationRequestType.CREATE,
                rejection_reason=None,
                created_by=actor.id,
            )
            await self.uow.products.add(product)

            if variants:
                for item in variants:
                    sku = (item.get("sku") or "").strip()
                    if not sku:
                        sku = f"{slug[:16]}-{uuid7().hex[:8]}".upper()
                    color = item.get("color") or item.get("color_name")
                    color_clean = color.strip() if color else None
                    size = item.get("size")
                    size_clean = size.strip() if size else None
                    stock_qty = int(item.get("stock_quantity", 0))
                    price_override = item.get("price_override")
                    variant = ProductVariantDomain(
                        product_id=product.id,
                        sku=sku,
                        size=size_clean,
                        color_name=color_clean,
                        color=color_clean,
                        color_hex=item.get("color_hex"),
                        price_override=Decimal(str(price_override))
                        if price_override is not None
                        else None,
                        stock_quantity=stock_qty,
                        created_by=actor.id,
                    )
                    await self.uow.variants.add(variant)

            await self.uow.commit()
            return product

    async def update_product(
        self,
        *,
        actor: UserDomain,
        product_id: UUID,
        category_id: UUID | None = None,
        brand_id: UUID | None = ...,  # type: ignore[assignment]
        title: str | None = None,
        slug: str | None = None,
        brand: str | None = ...,  # type: ignore[assignment]
        is_self_worked: bool | None = None,
        base_price: Decimal | None = None,
        price_usd: Decimal | None = ...,  # type: ignore[assignment]
        price_eur: Decimal | None = ...,  # type: ignore[assignment]
        material: str | None = ...,  # type: ignore[assignment]
        density: str | None = ...,  # type: ignore[assignment]
        composition: str | None = ...,  # type: ignore[assignment]
        print_method: str | None = ...,  # type: ignore[assignment]
        note: str | None = ...,  # type: ignore[assignment]
        description: str | None = None,
        attributes: dict[str, Any] | None = None,
        is_published: bool | None = None,
        is_hidden: int | None = None,
        is_limited: bool | None = None,
    ) -> ProductDomain:
        async with self.uow:
            product = await self.uow.products.get_by_id(
                product_id, include_unpublished=True
            )
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            await self._check_product_modify_permission(actor, product)

            is_substantial = False

            if category_id is not None and category_id != product.category_id:
                category = await self.uow.categories.get_by_id(category_id)
                if category is None:
                    raise EntityNotFoundError("Category not found")
                product.category_id = category_id
                is_substantial = True

            if title is not None:
                title_clean = title.strip()
                if not title_clean:
                    raise DomainValidationError("Product title cannot be empty")
                if title_clean != product.title:
                    product.title = title_clean
                    is_substantial = True

            if slug is not None:
                slug_clean = slug.strip()
                if not slug_clean:
                    raise DomainValidationError("Product slug cannot be empty")
                if slug_clean != product.slug:
                    product.slug = slug_clean
                    is_substantial = True

            if is_self_worked is not None and is_self_worked != product.is_self_worked:
                product.is_self_worked = is_self_worked
                is_substantial = True

            if brand_id is not ...:
                if brand_id is not None and getattr(self.uow, "brands", None):
                    brand_domain = await self.uow.brands.get_by_id(brand_id)
                    if brand_domain is None:
                        raise EntityNotFoundError("Brand not found")
                    if "*" not in actor.global_permissions:
                        member = await self.uow.brands.get_member(brand_id, actor.id)
                        if not member:
                            raise PermissionDeniedError(
                                "Membership in brand required to assign product to brand"
                            )
                    if brand_id != product.brand_id:
                        product.brand_id = brand_id
                        product.brand = brand_domain.name
                        product.brand_slug = brand_domain.slug
                        product.brand_is_deleted = brand_domain.is_deleted
                        is_substantial = True
                elif brand_id is None and product.brand_id is not None:
                    product.brand_id = None
                    product.brand_slug = None
                    product.brand_is_deleted = False
                    is_substantial = True

            if brand is not ...:
                brand_clean = brand.strip() if brand else None
                if brand_clean != product.brand:
                    product.brand = brand_clean
                    is_substantial = True

            if product.is_self_worked and not product.brand:
                product.brand = "self-worked"

            if material is not ...:
                mat_clean = material.strip() if material else None
                if mat_clean != product.material:
                    product.material = mat_clean
                    is_substantial = True

            if density is not ...:
                den_clean = density.strip() if density else None
                if den_clean != product.density:
                    product.density = den_clean
                    is_substantial = True

            if composition is not ...:
                comp_clean = composition.strip() if composition else None
                if comp_clean != product.composition:
                    product.composition = comp_clean
                    is_substantial = True

            if print_method is not ...:
                pm_clean = print_method.strip() if print_method else None
                if pm_clean != product.print_method:
                    product.print_method = pm_clean
                    is_substantial = True

            if note is not ...:
                note_clean = note.strip() if note else None
                if note_clean != product.note:
                    product.note = note_clean
                    is_substantial = True

            if description is not None and description != product.description:
                product.description = description
                is_substantial = True

            if base_price is not None:
                product.base_price = base_price

            if price_usd is not ...:
                product.price_usd = price_usd

            if price_eur is not ...:
                product.price_eur = price_eur

            if attributes is not None:
                product.attributes = attributes

            if is_published is not None:
                product.is_published = is_published

            if is_hidden is not None:
                if is_hidden not in (0, 1, 2):
                    raise DomainValidationError("is_hidden must be 0, 1, or 2")
                product.is_hidden = is_hidden

            if is_limited is not None:
                product.is_limited = is_limited

            if is_substantial:
                if product.moderation_status == ModerationStatus.APPROVED:
                    product.moderation_status = ModerationStatus.PENDING
                    product.request_type = ModerationRequestType.EDIT
                    product.rejection_reason = None
                elif product.moderation_status == ModerationStatus.REJECTED:
                    product.moderation_status = ModerationStatus.PENDING
                    product.rejection_reason = None
            elif product.moderation_status == ModerationStatus.REJECTED:
                product.moderation_status = ModerationStatus.PENDING
                product.rejection_reason = None

            product.updated_at = factory_now()
            await self.uow.products.update(product)
            await self.uow.commit()
            return product

    async def delete_product(self, *, actor: UserDomain, product_id: UUID) -> None:
        async with self.uow:
            product = await self.uow.products.get_by_id(
                product_id, include_unpublished=True
            )
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            await self._check_product_modify_permission(actor, product)

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
        size: str | None = None,
        color_name: str | None = None,
        color_hex: str | None = None,
        price_override: Decimal | None = None,
        stock_quantity: int = 0,
    ) -> ProductVariantDomain:
        sku = sku.strip()
        if not sku:
            raise DomainValidationError("SKU cannot be empty")

        async with self.uow:
            product = await self.uow.products.get_by_id(
                product_id, include_unpublished=True
            )
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            await self._check_product_modify_permission(actor, product)

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
        async with self.uow:
            variant = await self.uow.variants.get_by_id(variant_id)
            if variant is None:
                raise EntityNotFoundError("Variant not found")

            product = await self.uow.products.get_by_id(
                variant.product_id, include_unpublished=True
            )
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            await self._check_product_modify_permission(actor, product)

            if sku is not None:
                sku_clean = sku.strip()
                if not sku_clean:
                    raise DomainValidationError("SKU cannot be empty")
                variant.sku = sku_clean

            if size is not None:
                variant.size = size

            if color_name is not None:
                variant.color_name = color_name
                variant.color = color_name

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
        color: str | None = None,
        alt_text: str | None = None,
        sort_order: int = 0,
        is_main: bool = False,
    ) -> ProductImageDomain:
        url = url.strip()
        if not url:
            raise DomainValidationError("Image URL cannot be empty")

        async with self.uow:
            product = await self.uow.products.get_by_id(
                product_id, include_unpublished=True
            )
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            await self._check_product_modify_permission(actor, product)

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
                color=color.strip() if color else None,
                url=url,
                alt_text=alt_text,
                sort_order=sort_order,
                is_main=should_be_main,
                created_by=actor.id,
            )
            await self.uow.images.add(image)

            if product.moderation_status == ModerationStatus.APPROVED:
                product.moderation_status = ModerationStatus.PENDING
                product.request_type = ModerationRequestType.EDIT
                product.rejection_reason = None
                product.updated_at = factory_now()
                await self.uow.products.update(product)
            elif product.moderation_status == ModerationStatus.REJECTED:
                product.moderation_status = ModerationStatus.PENDING
                product.rejection_reason = None
                product.updated_at = factory_now()
                await self.uow.products.update(product)

            await self.uow.commit()
            return image

    @staticmethod
    def _detect_image_format(data: bytes) -> tuple[str, str]:
        if len(data) < 12:
            raise DomainValidationError("Invalid or corrupted image file")

        # JPEG: \xff\xd8\xff
        if data.startswith(b"\xff\xd8\xff"):
            return "jpg", "image/jpeg"

        # PNG: \x89PNG\r\n\x1a\n
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png", "image/png"

        # WebP: RIFF....WEBP
        if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "webp", "image/webp"

        raise DomainValidationError(
            "Unsupported image format. Allowed formats: JPEG, PNG, WebP"
        )

    async def upload_product_image(
        self,
        *,
        actor: UserDomain,
        product_id: UUID,
        file_data: bytes,
        color: str | None = None,
        alt_text: str | None = None,
        sort_order: int = 0,
        is_main: bool = False,
    ) -> ProductImageDomain:
        if len(file_data) > 5 * 1024 * 1024:
            raise DomainValidationError("File size exceeds 5 MB limit")

        ext, content_type = self._detect_image_format(file_data)

        if not self.storage:
            raise DomainValidationError("File storage is not configured")

        async with self.uow:
            product = await self.uow.products.get_by_id(
                product_id, include_unpublished=True
            )
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            await self._check_product_modify_permission(actor, product)

            image_id = uuid7()
            key = f"products/{product_id}/{image_id}.{ext}"
            public_url = await self.storage.upload_file(
                key=key,
                data=file_data,
                content_type=content_type,
            )

            existing_images = await self.uow.images.list_by_product_id(product_id)
            should_be_main = is_main or len(existing_images) == 0

            if should_be_main:
                await self.uow.images.unset_main_for_product(product_id)

            image = ProductImageDomain(
                id=image_id,
                product_id=product_id,
                url=public_url,
                color=color.strip() if color else None,
                alt_text=alt_text,
                sort_order=sort_order,
                is_main=should_be_main,
                created_by=actor.id,
            )
            await self.uow.images.add(image)

            if product.moderation_status == ModerationStatus.APPROVED:
                product.moderation_status = ModerationStatus.PENDING
                product.request_type = ModerationRequestType.EDIT
                product.rejection_reason = None
                product.updated_at = factory_now()
                await self.uow.products.update(product)
            elif product.moderation_status == ModerationStatus.REJECTED:
                product.moderation_status = ModerationStatus.PENDING
                product.rejection_reason = None
                product.updated_at = factory_now()
                await self.uow.products.update(product)

            await self.uow.commit()
            return image

    async def search(self, query: str, limit: int = 10) -> SearchResultDomain:
        clean_q = query.strip()
        if len(clean_q) < 2:
            raise DomainValidationError("Search query must be at least 2 characters")
        if len(clean_q) > 100:
            raise DomainValidationError("Search query must not exceed 100 characters")

        async with self.uow:
            products = await self.uow.products.search_products(clean_q, limit=limit)
            brands = await self.uow.products.search_brands(clean_q, limit=limit)
            variants = await self.uow.variants.search_variants(clean_q, limit=limit)
            return SearchResultDomain(
                products=products,
                brands=brands,
                variants=variants,
            )

    async def delete_image(
        self, *, actor: UserDomain, product_id: UUID, image_id: UUID
    ) -> None:
        async with self.uow:
            product = await self.uow.products.get_by_id(
                product_id, include_unpublished=True
            )
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            await self._check_product_modify_permission(actor, product)

            image = await self.uow.images.get_by_id(image_id)
            if image is None or image.product_id != product_id:
                raise EntityNotFoundError("Image not found")

            await self.uow.images.delete(image_id)

            if product.moderation_status == ModerationStatus.APPROVED:
                product.moderation_status = ModerationStatus.PENDING
                product.request_type = ModerationRequestType.EDIT
                product.rejection_reason = None
                product.updated_at = factory_now()
                await self.uow.products.update(product)
            elif product.moderation_status == ModerationStatus.REJECTED:
                product.moderation_status = ModerationStatus.PENDING
                product.rejection_reason = None
                product.updated_at = factory_now()
                await self.uow.products.update(product)

            await self.uow.commit()

    async def list_pending_products(
        self,
        *,
        actor: UserDomain,
        request_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductDomain], int]:
        self._check_moderator_permission(actor)
        async with self.uow:
            return await self.uow.products.list_pending_products(
                request_type=request_type, limit=limit, offset=offset
            )

    async def count_pending_products(self, *, actor: UserDomain) -> int:
        self._check_moderator_permission(actor)
        async with self.uow:
            return await self.uow.products.count_pending_products()

    async def approve_product(
        self, *, actor: UserDomain, product_id: UUID
    ) -> ProductDomain:
        self._check_moderator_permission(actor)
        async with self.uow:
            product = await self.uow.products.get_by_id(
                product_id, include_unpublished=True
            )
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            product.moderation_status = ModerationStatus.APPROVED
            product.rejection_reason = None
            product.updated_at = factory_now()
            await self.uow.products.update(product)
            await self.uow.commit()

        target_user = product.creator_id or product.created_by
        if target_user and self.notification_service is not None:
            await self.notification_service.notify_user(
                user_id=target_user,
                title="Заявка одобрена",
                body=f"Товар «{product.title}» прошёл проверку и опубликован.",
                link=f"/products/{product.slug}",
                send_email=False,
            )

        return product

    async def reject_product(
        self, *, actor: UserDomain, product_id: UUID, reason: str | None = None
    ) -> ProductDomain:
        self._check_moderator_permission(actor)
        clean_reason = reason.strip() if reason and reason.strip() else None
        async with self.uow:
            product = await self.uow.products.get_by_id(
                product_id, include_unpublished=True
            )
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            product.moderation_status = ModerationStatus.REJECTED
            product.rejection_reason = clean_reason
            product.updated_at = factory_now()
            await self.uow.products.update(product)
            await self.uow.commit()

        target_user = product.creator_id or product.created_by
        if target_user and self.notification_service is not None:
            body_text = (
                f"Отклонено: {clean_reason}"
                if clean_reason
                else "Отклонено: Причина не указана"
            )
            await self.notification_service.notify_user(
                user_id=target_user,
                title="Заявка отклонена",
                body=body_text,
                link=f"/creator/products/{product.slug}/edit",
                send_email=True,
            )

        return product
