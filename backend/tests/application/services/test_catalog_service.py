from decimal import Decimal

import pytest
from uuid6 import uuid7

from src.application.services import CatalogService
from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from src.domain.models import UserDomain


@pytest.fixture
def admin_user():
    return UserDomain(
        id=uuid7(),
        login="admin",
        global_permissions=["catalog:manage"],
    )


@pytest.fixture
def regular_user():
    return UserDomain(
        id=uuid7(),
        login="regular",
        global_permissions=[],
    )


@pytest.mark.anyio
async def test_admin_category_crud_and_cycle_protection(
    catalog_uow, admin_user, regular_user
):
    service = CatalogService(catalog_uow)

    # Regular user cannot create category
    with pytest.raises(PermissionDeniedError):
        await service.create_category(
            actor=regular_user,
            name="Shoes",
            slug="shoes",
        )

    # Admin creates root category
    root_cat = await service.create_category(
        actor=admin_user,
        name="Clothing",
        slug="clothing",
    )
    assert root_cat.name == "Clothing"
    assert root_cat.parent_id is None

    # Admin creates subcategory
    sub_cat = await service.create_category(
        actor=admin_user,
        name="Men's Clothing",
        slug="mens-clothing",
        parent_id=root_cat.id,
    )
    assert sub_cat.parent_id == root_cat.id

    # Self-parent is rejected
    with pytest.raises(DomainValidationError, match="own parent"):
        await service.update_category(
            actor=admin_user,
            category_id=root_cat.id,
            parent_id=root_cat.id,
        )

    # Cyclic hierarchy is rejected (setting root's parent to sub)
    with pytest.raises(DomainValidationError, match="Cyclic"):
        await service.update_category(
            actor=admin_user,
            category_id=root_cat.id,
            parent_id=sub_cat.id,
        )

    # List categories
    cats = await service.get_categories()
    assert len(cats) == 2


@pytest.mark.anyio
async def test_product_crud_and_detail(catalog_uow, admin_user):
    service = CatalogService(catalog_uow)
    cat = await service.create_category(
        actor=admin_user, name="Electronics", slug="electronics"
    )

    # Create published product
    prod = await service.create_product(
        actor=admin_user,
        category_id=cat.id,
        title="Smartphone X",
        slug="smartphone-x",
        base_price=Decimal("999.99"),
        description="Flagship smartphone",
        attributes={"storage": "128GB"},
        is_published=True,
    )
    assert prod.title == "Smartphone X"

    # Add variant
    variant = await service.create_variant(
        actor=admin_user,
        product_id=prod.id,
        sku="SPX-BLK-128",
        size="Standard",
        color_name="Black",
        color_hex="#000000",
        stock_quantity=50,
    )
    assert variant.sku == "SPX-BLK-128"

    # Add image (first image should become main automatically)
    img1 = await service.add_image(
        actor=admin_user,
        product_id=prod.id,
        url="https://example.com/img1.jpg",
    )
    assert img1.is_main is True

    # Add second image with is_main=True (should unset img1)
    img2 = await service.add_image(
        actor=admin_user,
        product_id=prod.id,
        url="https://example.com/img2.jpg",
        is_main=True,
    )
    assert img2.is_main is True
    # Verify img1 is no longer main
    stored_img1 = await catalog_uow.images.get_by_id(img1.id)
    assert stored_img1.is_main is False

    # Get product detail
    product_res, variants, images = await service.get_product_detail("smartphone-x")
    assert product_res.id == prod.id
    assert len(variants) == 1
    assert len(images) == 2

    # Filtering in list_products
    prods, total = await service.list_products(
        category_id=cat.id,
        min_price=Decimal("500"),
        max_price=Decimal("1500"),
        search="phone",
    )
    assert total == 1
    assert prods[0].id == prod.id

    # Soft delete product
    await service.delete_product(actor=admin_user, product_id=prod.id)
    # Detail on deleted product raises EntityNotFoundError
    with pytest.raises(EntityNotFoundError):
        await service.get_product_detail("smartphone-x")
