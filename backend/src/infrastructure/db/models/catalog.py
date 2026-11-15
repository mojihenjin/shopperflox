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
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

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
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        CheckConstraint("base_price >= 0", name="chk_products_base_price_non_negative"),
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
    size: Mapped[str] = mapped_column(String(64), nullable=False)
    color_name: Mapped[str] = mapped_column(String(64), nullable=False)
    color_hex: Mapped[str | None] = mapped_column(String(32), nullable=True)
    price_override: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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
