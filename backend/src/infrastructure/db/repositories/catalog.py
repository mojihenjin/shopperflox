from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from src.domain.models import (
    BrandSearchResult,
    CategoryDomain,
    FavoriteDomain,
    ModerationRequestType,
    ModerationStatus,
    ProductDomain,
    ProductImageDomain,
    ProductVariantDomain,
)
from src.infrastructure.db.models import (
    BrandModel,
    CategoryModel,
    FavoriteModel,
    ProductImageModel,
    ProductModel,
    ProductVariantModel,
)


class SqlAlchemyCategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, model: CategoryModel) -> CategoryDomain:
        return CategoryDomain(
            id=model.id,
            name=model.name,
            slug=model.slug,
            created_by=model.created_by,
            parent_id=model.parent_id,
            sort_order=model.sort_order,
            created_at=model.created_at,
        )

    async def get_by_id(self, category_id: UUID) -> CategoryDomain | None:
        model = await self.session.get(CategoryModel, category_id)
        return self._to_domain(model) if model else None

    async def get_by_slug(self, slug: str) -> CategoryDomain | None:
        stmt = select(CategoryModel).where(CategoryModel.slug == slug)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_all(self) -> list[CategoryDomain]:
        stmt = select(CategoryModel).order_by(
            CategoryModel.sort_order.asc(), CategoryModel.name.asc()
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def add(self, category: CategoryDomain) -> None:
        model = CategoryModel(
            id=category.id,
            name=category.name,
            slug=category.slug,
            parent_id=category.parent_id,
            sort_order=category.sort_order,
            created_by=category.created_by,
            created_at=category.created_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Category with slug '{category.slug}' already exists"
            ) from exc

    async def update(self, category: CategoryDomain) -> None:
        model = await self.session.get(CategoryModel, category.id)
        if model is None:
            raise EntityNotFoundError("Category not found")
        model.name = category.name
        model.slug = category.slug
        model.parent_id = category.parent_id
        model.sort_order = category.sort_order
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Category with slug '{category.slug}' already exists"
            ) from exc

    async def delete(self, category_id: UUID) -> None:
        stmt = delete(CategoryModel).where(CategoryModel.id == category_id)
        await self.session.execute(stmt)
        await self.session.flush()


class SqlAlchemyProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(
        self, model: ProductModel, brand_model: BrandModel | None = None
    ) -> ProductDomain:
        brand_name = model.brand
        brand_slug = None
        brand_logo_url = None
        brand_his_url = None
        brand_is_verified = False
        brand_is_deleted = False
        rel = brand_model
        if rel is None and "brand_rel" in model.__dict__:
            rel = model.__dict__["brand_rel"]

        if rel is not None:
            brand_name = rel.name
            brand_slug = rel.slug
            brand_logo_url = rel.logo_url
            brand_his_url = rel.his_url
            brand_is_verified = rel.is_verified
            brand_is_deleted = rel.is_deleted

        return ProductDomain(
            id=model.id,
            category_id=model.category_id,
            creator_id=model.creator_id,
            brand_id=model.brand_id,
            title=model.title,
            slug=model.slug,
            brand=brand_name,
            brand_slug=brand_slug,
            brand_logo_url=brand_logo_url,
            brand_his_url=brand_his_url,
            brand_is_verified=brand_is_verified,
            brand_is_deleted=brand_is_deleted,
            is_self_worked=model.is_self_worked,
            base_price=model.base_price,
            price_usd=model.price_usd,
            price_eur=model.price_eur,
            material=model.material,
            density=model.density,
            composition=model.composition,
            print_method=model.print_method,
            note=model.note,
            created_by=model.created_by,
            description=model.description,
            attributes=dict(model.attributes) if model.attributes else {},
            is_published=model.is_published,
            is_hidden=model.is_hidden,
            is_limited=model.is_limited,
            views_count=model.views_count,
            orders_count=model.orders_count,
            moderation_status=ModerationStatus(model.moderation_status)
            if model.moderation_status
            else ModerationStatus.PENDING,
            request_type=ModerationRequestType(model.request_type)
            if model.request_type
            else ModerationRequestType.CREATE,
            rejection_reason=model.rejection_reason,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    async def get_by_id(
        self, product_id: UUID, *, include_unpublished: bool = False
    ) -> ProductDomain | None:
        stmt = (
            select(ProductModel, BrandModel)
            .outerjoin(BrandModel, ProductModel.brand_id == BrandModel.id)
            .where(ProductModel.id == product_id, ProductModel.deleted_at.is_(None))
        )
        if not include_unpublished:
            stmt = stmt.where(ProductModel.is_published.is_(True))
        result = await self.session.execute(stmt)
        row = result.first()
        if not row:
            return None
        model, brand_model = row
        return self._to_domain(model, brand_model)

    async def get_by_slug(
        self, slug: str, *, include_unpublished: bool = False
    ) -> ProductDomain | None:
        stmt = (
            select(ProductModel, BrandModel)
            .outerjoin(BrandModel, ProductModel.brand_id == BrandModel.id)
            .where(ProductModel.slug == slug, ProductModel.deleted_at.is_(None))
        )
        if not include_unpublished:
            stmt = stmt.where(ProductModel.is_published.is_(True))
        result = await self.session.execute(stmt)
        row = result.first()
        if not row:
            return None
        model, brand_model = row
        return self._to_domain(model, brand_model)

    async def list_catalog(
        self,
        *,
        category_id: UUID | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        search: str | None = None,
        size: str | None = None,
        color: str | None = None,
        is_limited: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductDomain], int]:
        base_filters = [
            ProductModel.is_published.is_(True),
            ProductModel.deleted_at.is_(None),
            ProductModel.is_hidden == 0,
            ProductModel.moderation_status == "approved",
            or_(BrandModel.id.is_(None), BrandModel.is_deleted.is_(False)),
        ]
        if category_id is not None:
            base_filters.append(ProductModel.category_id == category_id)
        if min_price is not None:
            base_filters.append(ProductModel.base_price >= min_price)
        if max_price is not None:
            base_filters.append(ProductModel.base_price <= max_price)
        if is_limited is not None:
            base_filters.append(ProductModel.is_limited.is_(is_limited))
        if search:
            search_pattern = f"%{search.strip()}%"
            base_filters.append(
                or_(
                    ProductModel.title.ilike(search_pattern),
                    ProductModel.description.ilike(search_pattern),
                )
            )
        if size:
            size_clean = size.strip()
            size_subq = select(ProductVariantModel.product_id).where(
                ProductVariantModel.stock_quantity > 0,
                func.lower(ProductVariantModel.size) == func.lower(size_clean),
            )
            base_filters.append(ProductModel.id.in_(size_subq))
        if color:
            color_pattern = f"%{color.strip()}%"
            var_color_subq = select(ProductVariantModel.product_id).where(
                ProductVariantModel.color_name.ilike(color_pattern)
            )
            img_color_subq = select(ProductImageModel.product_id).where(
                ProductImageModel.color.ilike(color_pattern)
            )
            base_filters.append(
                or_(
                    ProductModel.id.in_(var_color_subq),
                    ProductModel.id.in_(img_color_subq),
                )
            )

        count_stmt = (
            select(func.count(ProductModel.id))
            .outerjoin(BrandModel, ProductModel.brand_id == BrandModel.id)
            .where(*base_filters)
        )
        count_res = await self.session.execute(count_stmt)
        total_count = count_res.scalar() or 0

        data_stmt = (
            select(ProductModel, BrandModel)
            .outerjoin(BrandModel, ProductModel.brand_id == BrandModel.id)
            .where(*base_filters)
            .order_by(ProductModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        data_res = await self.session.execute(data_stmt)
        rows = data_res.all()
        products = [self._to_domain(m, b) for m, b in rows]

        if products:
            p_ids = [p.id for p in products]
            v_stmt = (
                select(ProductVariantModel)
                .where(ProductVariantModel.product_id.in_(p_ids))
                .order_by(ProductVariantModel.created_at.asc())
            )
            v_res = await self.session.execute(v_stmt)
            variants_map: dict[UUID, list[ProductVariantDomain]] = {
                pid: [] for pid in p_ids
            }
            for vm in v_res.scalars().all():
                v_domain = ProductVariantDomain(
                    id=vm.id,
                    product_id=vm.product_id,
                    sku=vm.sku,
                    size=vm.size,
                    color_name=vm.color_name,
                    color=vm.color_name,
                    color_hex=vm.color_hex,
                    price_override=vm.price_override,
                    stock_quantity=vm.stock_quantity,
                    orders_count=vm.orders_count,
                    created_by=vm.created_by,
                    created_at=vm.created_at,
                    updated_at=vm.updated_at,
                )
                variants_map[vm.product_id].append(v_domain)

            i_stmt = (
                select(ProductImageModel)
                .where(ProductImageModel.product_id.in_(p_ids))
                .order_by(
                    ProductImageModel.sort_order.asc(),
                    ProductImageModel.created_at.asc(),
                )
            )
            i_res = await self.session.execute(i_stmt)
            images_map: dict[UUID, list[ProductImageDomain]] = {
                pid: [] for pid in p_ids
            }
            for im in i_res.scalars().all():
                i_domain = ProductImageDomain(
                    id=im.id,
                    product_id=im.product_id,
                    url=im.url,
                    created_by=im.created_by,
                    variant_id=im.variant_id,
                    color=im.color,
                    alt_text=im.alt_text,
                    sort_order=im.sort_order,
                    is_main=im.is_main,
                    created_at=im.created_at,
                )
                images_map[im.product_id].append(i_domain)

            for p in products:
                p.variants = variants_map.get(p.id, [])
                p.images = images_map.get(p.id, [])

        return products, total_count

    async def increment_views(self, product_id: UUID) -> None:
        stmt = (
            update(ProductModel)
            .where(ProductModel.id == product_id)
            .values(views_count=ProductModel.views_count + 1)
        )
        await self.session.execute(stmt)

    async def increment_orders(self, product_id: UUID, quantity: int) -> None:
        stmt = (
            update(ProductModel)
            .where(ProductModel.id == product_id)
            .values(orders_count=ProductModel.orders_count + quantity)
        )
        await self.session.execute(stmt)

    async def add(self, product: ProductDomain) -> None:
        model = ProductModel(
            id=product.id,
            category_id=product.category_id,
            creator_id=product.creator_id,
            brand_id=product.brand_id,
            title=product.title,
            slug=product.slug,
            brand=product.brand,
            is_self_worked=product.is_self_worked,
            base_price=product.base_price,
            price_usd=product.price_usd,
            price_eur=product.price_eur,
            material=product.material,
            density=product.density,
            composition=product.composition,
            print_method=product.print_method,
            note=product.note,
            description=product.description,
            attributes=product.attributes,
            is_published=product.is_published,
            is_hidden=product.is_hidden,
            is_limited=product.is_limited,
            views_count=product.views_count,
            orders_count=product.orders_count,
            moderation_status=str(product.moderation_status.value)
            if isinstance(product.moderation_status, ModerationStatus)
            else str(product.moderation_status),
            request_type=str(product.request_type.value)
            if isinstance(product.request_type, ModerationRequestType)
            else str(product.request_type),
            rejection_reason=product.rejection_reason,
            created_by=product.created_by,
            created_at=product.created_at,
            updated_at=product.updated_at,
            deleted_at=product.deleted_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Product with slug '{product.slug}' already exists"
            ) from exc

    async def update(self, product: ProductDomain) -> None:
        model = await self.session.get(ProductModel, product.id)
        if model is None or model.deleted_at is not None:
            raise EntityNotFoundError("Product not found")
        model.category_id = product.category_id
        model.creator_id = product.creator_id
        model.brand_id = product.brand_id
        model.title = product.title
        model.slug = product.slug
        model.brand = product.brand
        model.is_self_worked = product.is_self_worked
        model.base_price = product.base_price
        model.price_usd = product.price_usd
        model.price_eur = product.price_eur
        model.material = product.material
        model.density = product.density
        model.composition = product.composition
        model.print_method = product.print_method
        model.note = product.note
        model.description = product.description
        model.attributes = product.attributes
        model.is_published = product.is_published
        model.is_hidden = product.is_hidden
        model.is_limited = product.is_limited
        model.views_count = product.views_count
        model.orders_count = product.orders_count
        model.moderation_status = (
            str(product.moderation_status.value)
            if isinstance(product.moderation_status, ModerationStatus)
            else str(product.moderation_status)
        )
        model.request_type = (
            str(product.request_type.value)
            if isinstance(product.request_type, ModerationRequestType)
            else str(product.request_type)
        )
        model.rejection_reason = product.rejection_reason
        model.updated_at = product.updated_at
        model.deleted_at = product.deleted_at
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Product with slug '{product.slug}' already exists"
            ) from exc

    async def search_products(self, query: str, limit: int = 10) -> list[ProductDomain]:
        escaped = (
            query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        if not escaped:
            return []
        pattern = f"%{escaped}%"
        stmt = (
            select(ProductModel, BrandModel)
            .outerjoin(BrandModel, ProductModel.brand_id == BrandModel.id)
            .where(
                ProductModel.is_published.is_(True),
                ProductModel.deleted_at.is_(None),
                ProductModel.is_hidden == 0,
                ProductModel.moderation_status == "approved",
                or_(BrandModel.id.is_(None), BrandModel.is_deleted.is_(False)),
                or_(
                    ProductModel.title.ilike(pattern, escape="\\"),
                    ProductModel.description.ilike(pattern, escape="\\"),
                    ProductModel.brand.ilike(pattern, escape="\\"),
                ),
            )
            .order_by(ProductModel.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [self._to_domain(m, b) for m, b in rows]

    async def search_brands(
        self, query: str, limit: int = 10
    ) -> list[BrandSearchResult]:
        escaped = (
            query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        if not escaped:
            return []
        pattern = f"%{escaped}%"
        stmt = (
            select(ProductModel.brand, func.count(ProductModel.id))
            .outerjoin(BrandModel, ProductModel.brand_id == BrandModel.id)
            .where(
                ProductModel.is_published.is_(True),
                ProductModel.deleted_at.is_(None),
                ProductModel.is_hidden == 0,
                ProductModel.moderation_status == "approved",
                or_(BrandModel.id.is_(None), BrandModel.is_deleted.is_(False)),
                ProductModel.brand.isnot(None),
                ProductModel.brand != "",
                ProductModel.brand.ilike(pattern, escape="\\"),
            )
            .group_by(ProductModel.brand)
            .order_by(func.count(ProductModel.id).desc(), ProductModel.brand.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [BrandSearchResult(name=row[0], products_count=row[1]) for row in rows]

    async def list_pending_products(
        self,
        *,
        request_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductDomain], int]:
        filters = [
            ProductModel.moderation_status == "pending",
            ProductModel.deleted_at.is_(None),
        ]
        if request_type:
            filters.append(ProductModel.request_type == request_type)

        count_stmt = select(func.count(ProductModel.id)).where(*filters)
        count_res = await self.session.execute(count_stmt)
        total_count = count_res.scalar() or 0

        data_stmt = (
            select(ProductModel, BrandModel)
            .outerjoin(BrandModel, ProductModel.brand_id == BrandModel.id)
            .where(*filters)
            .order_by(ProductModel.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        data_res = await self.session.execute(data_stmt)
        rows = data_res.all()
        return [self._to_domain(m, b) for m, b in rows], total_count

    async def count_pending_products(self) -> int:
        stmt = select(func.count(ProductModel.id)).where(
            ProductModel.moderation_status == "pending",
            ProductModel.deleted_at.is_(None),
        )
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def update_brand_name_for_products(
        self, brand_id: UUID, brand_name: str
    ) -> None:
        stmt = (
            update(ProductModel)
            .where(ProductModel.brand_id == brand_id)
            .values(brand=brand_name)
        )
        await self.session.execute(stmt)
        await self.session.flush()


class SqlAlchemyProductVariantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, model: ProductVariantModel) -> ProductVariantDomain:
        return ProductVariantDomain(
            id=model.id,
            product_id=model.product_id,
            sku=model.sku,
            size=model.size,
            color_name=model.color_name,
            color=model.color_name,
            created_by=model.created_by,
            color_hex=model.color_hex,
            price_override=model.price_override,
            stock_quantity=model.stock_quantity,
            orders_count=model.orders_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_by_id(self, variant_id: UUID) -> ProductVariantDomain | None:
        model = await self.session.get(ProductVariantModel, variant_id)
        return self._to_domain(model) if model else None

    async def get_by_sku(self, sku: str) -> ProductVariantDomain | None:
        stmt = select(ProductVariantModel).where(ProductVariantModel.sku == sku)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_ids_for_update(
        self, variant_ids: list[UUID]
    ) -> list[ProductVariantDomain]:
        if not variant_ids:
            return []
        stmt = (
            select(ProductVariantModel)
            .where(ProductVariantModel.id.in_(variant_ids))
            .order_by(ProductVariantModel.id.asc())
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def list_by_product_id(self, product_id: UUID) -> list[ProductVariantDomain]:
        stmt = (
            select(ProductVariantModel)
            .where(ProductVariantModel.product_id == product_id)
            .order_by(ProductVariantModel.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def search_variants(
        self, query: str, limit: int = 10
    ) -> list[ProductVariantDomain]:
        escaped = (
            query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        if not escaped:
            return []
        pattern = f"%{escaped}%"
        stmt = (
            select(ProductVariantModel)
            .join(ProductModel, ProductVariantModel.product_id == ProductModel.id)
            .where(
                ProductModel.is_published.is_(True),
                ProductModel.deleted_at.is_(None),
                ProductModel.is_hidden == 0,
                ProductModel.moderation_status == "approved",
                or_(
                    ProductVariantModel.sku.ilike(pattern, escape="\\"),
                    ProductVariantModel.color_name.ilike(pattern, escape="\\"),
                    ProductVariantModel.size.ilike(pattern, escape="\\"),
                ),
            )
            .order_by(ProductVariantModel.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def add(self, variant: ProductVariantDomain) -> None:
        model = ProductVariantModel(
            id=variant.id,
            product_id=variant.product_id,
            sku=variant.sku,
            size=variant.size,
            color_name=variant.color_name or variant.color,
            color_hex=variant.color_hex,
            price_override=variant.price_override,
            stock_quantity=variant.stock_quantity,
            orders_count=variant.orders_count,
            created_by=variant.created_by,
            created_at=variant.created_at,
            updated_at=variant.updated_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Variant with SKU '{variant.sku}' already exists"
            ) from exc

    async def increment_orders(self, variant_id: UUID, quantity: int) -> None:
        stmt = (
            update(ProductVariantModel)
            .where(ProductVariantModel.id == variant_id)
            .values(orders_count=ProductVariantModel.orders_count + quantity)
        )
        await self.session.execute(stmt)

    async def update(self, variant: ProductVariantDomain) -> None:
        model = await self.session.get(ProductVariantModel, variant.id)
        if model is None:
            raise EntityNotFoundError("Variant not found")
        model.sku = variant.sku
        model.size = variant.size
        model.color_name = variant.color_name or variant.color
        model.color_hex = variant.color_hex
        model.price_override = variant.price_override
        model.stock_quantity = variant.stock_quantity
        model.updated_at = variant.updated_at
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Variant with SKU '{variant.sku}' already exists"
            ) from exc

    async def delete(self, variant_id: UUID) -> None:
        stmt = delete(ProductVariantModel).where(ProductVariantModel.id == variant_id)
        await self.session.execute(stmt)
        await self.session.flush()


class SqlAlchemyProductImageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, model: ProductImageModel) -> ProductImageDomain:
        return ProductImageDomain(
            id=model.id,
            product_id=model.product_id,
            url=model.url,
            created_by=model.created_by,
            variant_id=model.variant_id,
            color=model.color,
            alt_text=model.alt_text,
            sort_order=model.sort_order,
            is_main=model.is_main,
            created_at=model.created_at,
        )

    async def get_by_id(self, image_id: UUID) -> ProductImageDomain | None:
        model = await self.session.get(ProductImageModel, image_id)
        return self._to_domain(model) if model else None

    async def list_by_product_id(self, product_id: UUID) -> list[ProductImageDomain]:
        stmt = (
            select(ProductImageModel)
            .where(ProductImageModel.product_id == product_id)
            .order_by(
                ProductImageModel.sort_order.asc(),
                ProductImageModel.created_at.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def unset_main_for_product(self, product_id: UUID) -> None:
        stmt = (
            update(ProductImageModel)
            .where(
                ProductImageModel.product_id == product_id,
                ProductImageModel.is_main.is_(True),
            )
            .values(is_main=False)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def add(self, image: ProductImageDomain) -> None:
        model = ProductImageModel(
            id=image.id,
            product_id=image.product_id,
            variant_id=image.variant_id,
            color=image.color,
            url=image.url,
            alt_text=image.alt_text,
            sort_order=image.sort_order,
            is_main=image.is_main,
            created_by=image.created_by,
            created_at=image.created_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                "Product already has a main image or image duplicate error"
            ) from exc

    async def update(self, image: ProductImageDomain) -> None:
        model = await self.session.get(ProductImageModel, image.id)
        if model is None:
            raise EntityNotFoundError("Image not found")
        model.url = image.url
        model.variant_id = image.variant_id
        model.color = image.color
        model.alt_text = image.alt_text
        model.sort_order = image.sort_order
        model.is_main = image.is_main
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError("Image constraint violation") from exc

    async def delete(self, image_id: UUID) -> None:
        stmt = delete(ProductImageModel).where(ProductImageModel.id == image_id)
        await self.session.execute(stmt)
        await self.session.flush()


class SqlAlchemyFavoriteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def exists(self, user_id: UUID, product_id: UUID) -> bool:
        stmt = (
            select(func.count())
            .select_from(FavoriteModel)
            .where(
                FavoriteModel.user_id == user_id,
                FavoriteModel.product_id == product_id,
            )
        )
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0

    async def list_user_favorite_products(
        self, user_id: UUID, *, limit: int = 20, offset: int = 0
    ) -> tuple[list[ProductDomain], int]:
        join_condition = (FavoriteModel.product_id == ProductModel.id) & (
            FavoriteModel.user_id == user_id
        )
        filters = [
            ProductModel.is_published.is_(True),
            ProductModel.deleted_at.is_(None),
        ]

        count_stmt = (
            select(func.count(ProductModel.id))
            .select_from(FavoriteModel)
            .join(ProductModel, join_condition)
            .where(*filters)
        )
        count_res = await self.session.execute(count_stmt)
        total_count = count_res.scalar() or 0

        data_stmt = (
            select(ProductModel)
            .select_from(FavoriteModel)
            .join(ProductModel, join_condition)
            .where(*filters)
            .order_by(FavoriteModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        data_res = await self.session.execute(data_stmt)
        products = [
            ProductDomain(
                id=m.id,
                category_id=m.category_id,
                title=m.title,
                slug=m.slug,
                base_price=m.base_price,
                created_by=m.created_by,
                description=m.description,
                attributes=dict(m.attributes) if m.attributes else {},
                is_published=m.is_published,
                created_at=m.created_at,
                updated_at=m.updated_at,
                deleted_at=m.deleted_at,
            )
            for m in data_res.scalars().all()
        ]
        return products, total_count

    async def add(self, favorite: FavoriteDomain) -> None:
        model = FavoriteModel(
            user_id=favorite.user_id,
            product_id=favorite.product_id,
            created_by=favorite.created_by,
            created_at=favorite.created_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError:
            # Idempotent add: if already in favorites, rollback this flush savepoint
            pass

    async def delete(self, user_id: UUID, product_id: UUID) -> None:
        stmt = delete(FavoriteModel).where(
            FavoriteModel.user_id == user_id,
            FavoriteModel.product_id == product_id,
        )
        await self.session.execute(stmt)
        await self.session.flush()
