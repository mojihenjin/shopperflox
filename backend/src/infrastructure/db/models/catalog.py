from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index("uq_categories_slug", "slug", unique=True),
        Index("ix_categories_parent_id", "parent_id"),
    )


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    creator_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    brand_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_self_worked: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_eur: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_cny: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    material: Mapped[str | None] = mapped_column(String(255), nullable=True)
    density: Mapped[str | None] = mapped_column(String(128), nullable=True)
    composition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    print_method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_hidden: Mapped[int] = mapped_column(
        SmallInteger, default=0, server_default="0", nullable=False, index=True
    )
    is_limited: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    views_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    orders_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    moderation_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        nullable=False,
        index=True,
    )
    request_type: Mapped[str] = mapped_column(
        String(20),
        default="CREATE",
        server_default="CREATE",
        nullable=False,
        index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    brand_rel = relationship("BrandModel", foreign_keys=[brand_id])
    creator_rel = relationship("UserModel", foreign_keys=[creator_id])

    __table_args__ = (
        CheckConstraint("base_price >= 0", name="chk_products_base_price_non_negative"),
        CheckConstraint(
            "price_usd IS NULL OR price_usd >= 0",
            name="chk_products_price_usd_non_negative",
        ),
        CheckConstraint(
            "price_eur IS NULL OR price_eur >= 0",
            name="chk_products_price_eur_non_negative",
        ),
        CheckConstraint(
            "price_cny IS NULL OR price_cny >= 0",
            name="chk_products_price_cny_non_negative",
        ),
        CheckConstraint(
            "is_hidden IN (0, 1, 2)",
            name="chk_products_is_hidden_range",
        ),
        Index("ix_products_creator_id", "creator_id"),
        Index(
            "uq_products_slug_active",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
        Index("ix_products_category_id", "category_id"),
        Index(
            "ix_products_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index(
            "ix_products_brand_trgm",
            "brand",
            postgresql_using="gin",
            postgresql_ops={"brand": "gin_trgm_ops"},
        ),
    )


class ProductVariantModel(Base):
    __tablename__ = "product_variants"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color_hex: Mapped[str | None] = mapped_column(String(32), nullable=True)
    price_override: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index("uq_product_variants_sku", "sku", unique=True),
        CheckConstraint(
            "stock_quantity >= 0",
            name="chk_product_variants_stock_quantity_non_negative",
        ),
        CheckConstraint(
            "price_override IS NULL OR price_override >= 0",
            name="chk_product_variants_price_override_non_negative",
        ),
        Index("ix_product_variants_product_id", "product_id"),
        Index(
            "ix_product_variants_sku_trgm",
            "sku",
            postgresql_using="gin",
            postgresql_ops={"sku": "gin_trgm_ops"},
        ),
        Index(
            "ix_product_variants_color_name_trgm",
            "color_name",
            postgresql_using="gin",
            postgresql_ops={"color_name": "gin_trgm_ops"},
        ),
        Index(
            "ix_product_variants_size_trgm",
            "size",
            postgresql_using="gin",
            postgresql_ops={"size": "gin_trgm_ops"},
        ),
    )


class ProductImageModel(Base):
    __tablename__ = "product_images"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    color: Mapped[str | None] = mapped_column(String(100), nullable=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index(
            "uq_product_images_main",
            "product_id",
            unique=True,
            postgresql_where=text("is_main = TRUE"),
            sqlite_where=text("is_main = TRUE"),
        ),
        Index("ix_product_images_product_id", "product_id"),
        Index("ix_product_images_variant_id", "variant_id"),
        Index("ix_product_images_color", "color"),
    )


class FavoriteModel(Base):
    __tablename__ = "favorites"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index("ix_favorites_user_id", "user_id"),
        Index("ix_favorites_product_id", "product_id"),
    )
