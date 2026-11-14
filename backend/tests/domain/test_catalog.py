from decimal import Decimal
from uuid import UUID

from src.domain.models import (
    CategoryDomain,
    ProductDomain,
    ProductImageDomain,
    ProductVariantDomain,
)
from uuid6 import uuid7


def test_category_domain():
    author_id = uuid7()
    category = CategoryDomain(
        name="Shoes",
        slug="shoes",
        created_by=author_id,
        sort_order=10,
    )

    assert isinstance(category.id, UUID)
    assert category.name == "Shoes"
    assert category.slug == "shoes"
    assert category.parent_id is None
    assert category.sort_order == 10


def test_product_domain():
    author_id = uuid7()
    cat_id = uuid7()
    product = ProductDomain(
        category_id=cat_id,
        title="Running Shoes",
        slug="running-shoes",
        base_price=Decimal("99.99"),
        created_by=author_id,
        attributes={"gender": "unisex"},
    )

    assert isinstance(product.id, UUID)
    assert product.base_price == Decimal("99.99")
    assert product.attributes == {"gender": "unisex"}
    assert product.is_published is False
    assert product.deleted_at is None


def test_product_variant_domain():
    author_id = uuid7()
    prod_id = uuid7()
    variant = ProductVariantDomain(
        product_id=prod_id,
        sku="RUN-SHOES-BLK-42",
        size="42",
        color_name="Black",
        color_hex="#000000",
        price_override=Decimal("89.99"),
        stock_quantity=15,
        created_by=author_id,
    )

    assert isinstance(variant.id, UUID)
    assert variant.sku == "RUN-SHOES-BLK-42"
    assert variant.price_override == Decimal("89.99")
    assert variant.stock_quantity == 15


def test_product_image_domain():
    author_id = uuid7()
    prod_id = uuid7()
    img = ProductImageDomain(
        product_id=prod_id,
        url="https://example.com/shoes.jpg",
        alt_text="Front view",
        is_main=True,
        created_by=author_id,
    )

    assert isinstance(img.id, UUID)
    assert img.is_main is True
    assert img.sort_order == 0
