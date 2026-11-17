from decimal import Decimal
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.domain.models import (
    CategoryDomain,
    ProductDomain,
    ProductImageDomain,
    ProductVariantDomain,
)


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


def test_product_domain_multi_currency_and_characteristics():
    author_id = uuid7()
    creator_id = uuid7()
    cat_id = uuid7()
    product = ProductDomain(
        category_id=cat_id,
        creator_id=creator_id,
        title="Creator Sweatshirt",
        slug="creator-sweatshirt",
        brand="self-worked",
        is_self_worked=True,
        base_price=Decimal("3500.00"),
        price_usd=Decimal("38.50"),
        price_eur=Decimal("35.00"),
        material="Fleece",
        density="380 g/m²",
        composition="80% Cotton 20% Poly",
        print_method="DTG",
        note="Limited edition",
        created_by=author_id,
    )

    assert product.creator_id == creator_id
    assert product.is_self_worked is True
    assert product.brand == "self-worked"
    assert product.price_usd == Decimal("38.50")
    assert product.price_eur == Decimal("35.00")
    assert product.material == "Fleece"
    assert product.density == "380 g/m²"
    assert product.composition == "80% Cotton 20% Poly"
    assert product.print_method == "DTG"
    assert product.note == "Limited edition"


def test_product_domain_negative_currency_validation():

    from src.domain.exceptions import DomainValidationError

    author_id = uuid7()
    cat_id = uuid7()

    with pytest.raises(DomainValidationError, match="price_usd"):
        ProductDomain(
            category_id=cat_id,
            title="Invalid USD",
            slug="invalid-usd",
            base_price=Decimal("100"),
            price_usd=Decimal("-5.00"),
            created_by=author_id,
        )

    with pytest.raises(DomainValidationError, match="price_eur"):
        ProductDomain(
            category_id=cat_id,
            title="Invalid EUR",
            slug="invalid-eur",
            base_price=Decimal("100"),
            price_eur=Decimal("-1.00"),
            created_by=author_id,
        )

    with pytest.raises(DomainValidationError, match="price_cny"):
        ProductDomain(
            category_id=cat_id,
            title="Invalid CNY",
            slug="invalid-cny",
            base_price=Decimal("100"),
            price_cny=Decimal("-1.00"),
            created_by=author_id,
        )

    valid_prod = ProductDomain(
        category_id=cat_id,
        title="Valid Multi-currency",
        slug="valid-multicurrency",
        base_price=Decimal("100"),
        price_cny=Decimal("720.50"),
        created_by=author_id,
    )
    assert valid_prod.price_cny == Decimal("720.50")


def test_product_image_domain_with_color():
    author_id = uuid7()
    prod_id = uuid7()
    img = ProductImageDomain(
        product_id=prod_id,
        url="https://example.com/shoes-red.jpg",
        color="Crimson Red",
        sort_order=2,
        created_by=author_id,
    )

    assert img.color == "Crimson Red"
    assert img.sort_order == 2


def test_product_variant_color_alias():
    author_id = uuid7()
    prod_id = uuid7()
    v1 = ProductVariantDomain(
        product_id=prod_id,
        sku="TEST-SKU-1",
        color="Navy Blue",
        created_by=author_id,
    )
    assert v1.color == "Navy Blue"
    assert v1.color_name == "Navy Blue"

    v2 = ProductVariantDomain(
        product_id=prod_id,
        sku="TEST-SKU-2",
        color_name="Olive Green",
        created_by=author_id,
    )
    assert v2.color == "Olive Green"
    assert v2.color_name == "Olive Green"
