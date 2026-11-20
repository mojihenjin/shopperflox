from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import (
    OrderStatus,
    ProductSalesStats,
    SalesAnalyticsDomain,
    VariantSalesStats,
)
from src.infrastructure.db.models import (
    OrderItemModel,
    OrderModel,
    ProductModel,
    ProductVariantModel,
)


class SqlAlchemyAnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _compute_analytics_for_products(
        self, products: list[ProductModel]
    ) -> SalesAnalyticsDomain:
        if not products:
            return SalesAnalyticsDomain(
                total_views=0,
                total_units_sold=0,
                total_revenue={
                    "RUB": Decimal("0.00"),
                    "USD": Decimal("0.00"),
                    "EUR": Decimal("0.00"),
                    "CNY": Decimal("0.00"),
                },
                products=[],
            )

        product_ids = [p.id for p in products]

        # Fetch variants
        v_stmt = (
            select(ProductVariantModel)
            .where(ProductVariantModel.product_id.in_(product_ids))
            .order_by(ProductVariantModel.created_at.asc())
        )
        v_res = await self.session.execute(v_stmt)
        all_variants = v_res.scalars().all()

        variant_ids = [v.id for v in all_variants]

        # Aggregate order items by variant
        sales_by_variant: dict[UUID, tuple[int, Decimal]] = {}
        if variant_ids:
            agg_stmt = (
                select(
                    OrderItemModel.variant_id,
                    func.coalesce(func.sum(OrderItemModel.quantity), 0).label(
                        "total_quantity"
                    ),
                    func.coalesce(
                        func.sum(OrderItemModel.unit_price * OrderItemModel.quantity),
                        0,
                    ).label("total_revenue"),
                )
                .join(OrderModel, OrderItemModel.order_id == OrderModel.id)
                .where(
                    OrderItemModel.variant_id.in_(variant_ids),
                    OrderModel.status != OrderStatus.CANCELLED,
                )
                .group_by(OrderItemModel.variant_id)
            )
            agg_res = await self.session.execute(agg_stmt)
            for var_id, qty, rev in agg_res.all():
                sales_by_variant[var_id] = (int(qty), Decimal(str(rev)))

        # Group variants by product
        variants_by_product: dict[UUID, list[ProductVariantModel]] = {}
        for v in all_variants:
            variants_by_product.setdefault(v.product_id, []).append(v)

        product_stats_list: list[ProductSalesStats] = []
        total_views = 0
        total_units = 0
        total_rev_rub = Decimal("0.00")

        for p in products:
            p_variants = variants_by_product.get(p.id, [])
            variant_stats_list: list[VariantSalesStats] = []
            p_units = 0
            p_rev_rub = Decimal("0.00")

            for v in p_variants:
                v_qty, v_rev = sales_by_variant.get(v.id, (0, Decimal("0.00")))
                units = max(v_qty, v.orders_count)
                if units > 0 and v_rev == Decimal("0.00"):
                    price = (
                        v.price_override
                        if v.price_override is not None
                        else p.base_price
                    )
                    v_rev = Decimal(units) * price

                p_units += units
                p_rev_rub += v_rev

                variant_stats_list.append(
                    VariantSalesStats(
                        variant_id=v.id,
                        sku=v.sku,
                        color=v.color_name,
                        size=v.size,
                        stock_quantity=v.stock_quantity,
                        units_sold=units,
                        revenue={
                            "RUB": v_rev,
                            "USD": Decimal("0.00"),
                            "EUR": Decimal("0.00"),
                            "CNY": Decimal("0.00"),
                        },
                    )
                )

            final_p_units = max(p_units, p.orders_count)
            if final_p_units > 0 and p_rev_rub == Decimal("0.00"):
                p_rev_rub = Decimal(final_p_units) * p.base_price

            total_views += p.views_count
            total_units += final_p_units
            total_rev_rub += p_rev_rub

            product_stats_list.append(
                ProductSalesStats(
                    product_id=p.id,
                    title=p.title,
                    slug=p.slug,
                    views_count=p.views_count,
                    units_sold=final_p_units,
                    revenue={
                        "RUB": p_rev_rub,
                        "USD": Decimal("0.00"),
                        "EUR": Decimal("0.00"),
                        "CNY": Decimal("0.00"),
                    },
                    variants=variant_stats_list,
                )
            )

        return SalesAnalyticsDomain(
            total_views=total_views,
            total_units_sold=total_units,
            total_revenue={
                "RUB": total_rev_rub,
                "USD": Decimal("0.00"),
                "EUR": Decimal("0.00"),
                "CNY": Decimal("0.00"),
            },
            products=product_stats_list,
        )

    async def get_self_worked_analytics(self, user_id: UUID) -> SalesAnalyticsDomain:
        stmt = (
            select(ProductModel)
            .where(
                ProductModel.deleted_at.is_(None),
                ProductModel.brand_id.is_(None),
                or_(
                    ProductModel.creator_id == user_id,
                    ProductModel.created_by == user_id,
                ),
            )
            .order_by(ProductModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        products = list(res.scalars().all())
        return await self._compute_analytics_for_products(products)

    async def get_brand_analytics(self, brand_id: UUID) -> SalesAnalyticsDomain:
        stmt = (
            select(ProductModel)
            .where(
                ProductModel.deleted_at.is_(None),
                ProductModel.brand_id == brand_id,
            )
            .order_by(ProductModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        products = list(res.scalars().all())
        return await self._compute_analytics_for_products(products)
