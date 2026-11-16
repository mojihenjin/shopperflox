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
        global_permissions=["catalog:manage", "mod:approve_manager"],
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

    # Approve product
    await service.approve_product(actor=admin_user, product_id=prod.id)

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


@pytest.mark.anyio
async def test_creator_product_creation_and_authorization(catalog_uow, admin_user):
    service = CatalogService(catalog_uow)
    cat = await service.create_category(
        actor=admin_user, name="Streetwear", slug="streetwear"
    )

    creator1 = UserDomain(
        id=uuid7(),
        login="designer1",
        global_permissions=["creator:*"],
    )
    creator2 = UserDomain(
        id=uuid7(),
        login="designer2",
        global_permissions=["creator:products"],
    )

    # Creator1 creates product with is_self_worked and variants
    prod = await service.create_product(
        actor=creator1,
        category_id=cat.id,
        title="Custom Bomber",
        slug="custom-bomber",
        is_self_worked=True,
        base_price=Decimal("12000.00"),
        price_usd=Decimal("130.00"),
        price_eur=Decimal("120.00"),
        material="Nylon Satin",
        variants=[
            {"color": "Sage Green", "size": "M", "stock_quantity": 5},
            {"sku": "BOMB-BLK-L", "color": "Black", "size": "L", "stock_quantity": 10},
        ],
    )
    assert prod.creator_id == creator1.id
    assert prod.brand == "self-worked"
    assert prod.is_self_worked is True

    # Check variants created in UoW
    variants = await catalog_uow.variants.list_by_product_id(prod.id)
    assert len(variants) == 2
    skus = [v.sku for v in variants]
    assert "BOMB-BLK-L" in skus

    # Creator1 adds color-tagged image
    img = await service.add_image(
        actor=creator1,
        product_id=prod.id,
        url="https://example.com/green.jpg",
        color="Sage Green",
    )
    assert img.color == "Sage Green"

    # Creator2 cannot modify product
    with pytest.raises(PermissionDeniedError):
        await service.update_product(
            actor=creator2,
            product_id=prod.id,
            title="Unauthorized",
        )

    # Creator2 cannot add variant to creator1's product
    with pytest.raises(PermissionDeniedError):
        await service.create_variant(
            actor=creator2,
            product_id=prod.id,
            sku="HACK-1",
        )

    # Creator2 cannot update variant of creator1's product
    with pytest.raises(PermissionDeniedError):
        await service.update_variant(
            actor=creator2,
            variant_id=variants[0].id,
            stock_quantity=999,
        )

    # Creator1 CAN update variant
    updated_var = await service.update_variant(
        actor=creator1,
        variant_id=variants[0].id,
        stock_quantity=8,
    )
    assert updated_var.stock_quantity == 8

    # Admin CAN update variant
    admin_updated_var = await service.update_variant(
        actor=admin_user,
        variant_id=variants[0].id,
        stock_quantity=12,
    )
    assert admin_updated_var.stock_quantity == 12


@pytest.mark.anyio
async def test_generate_variant_sku_and_cyrillic_auto_sku(catalog_uow, admin_user):
    from src.application.services.catalog import (
        generate_variant_sku,
        transliterate_to_latin,
    )

    # Test transliteration
    assert transliterate_to_latin("ЛЕОПАРДОВЫЙ") == "leopardovyy"
    assert transliterate_to_latin("РОЗОВЫЙ") == "rozovyy"
    assert transliterate_to_latin("МАЛЕНЬКИЙ") == "malenkiy"

    # Test SKU generation uniqueness even with identical inputs
    sku_a = generate_variant_sku(
        product_slug="leopard-dress", color="ЛЕОПАРДОВЫЙ", size="МАЛЕНЬКИЙ"
    )
    sku_b = generate_variant_sku(
        product_slug="leopard-dress", color="ЛЕОПАРДОВЫЙ", size="МАЛЕНЬКИЙ"
    )
    assert sku_a != sku_b
    assert "LEOPARD" in sku_a
    assert "MALENKIY" in sku_a

    # Test used_skus set prevents duplicates
    used = set()
    sku_c = generate_variant_sku(
        product_slug="item", color="РОЗОВЫЙ", size="МАЛЕНЬКИЙ", used_skus=used
    )
    sku_d = generate_variant_sku(
        product_slug="item", color="РОЗОВЫЙ", size="МАЛЕНЬКИЙ", used_skus=used
    )
    assert sku_c != sku_d
    assert sku_c in used
    assert sku_d in used

    # Test CatalogService creation with cyrillic variants
    service = CatalogService(uow=catalog_uow)
    cat = await service.create_category(
        actor=admin_user,
        name="Летняя одежда",
        slug="summer-wear",
    )
    prod = await service.create_product(
        actor=admin_user,
        category_id=cat.id,
        title="Шелковая юбка",
        slug="shelkovaya-yubka",
        base_price=Decimal("4000.00"),
        variants=[
            {"color": "ЛЕОПАРДОВЫЙ", "size": "МАЛЕНЬКИЙ", "stock_quantity": 7},
            {"color": "РОЗОВЫЙ", "size": "МАЛЕНЬКИЙ", "stock_quantity": 14},
        ],
    )
    vars_list = await catalog_uow.variants.list_by_product_id(prod.id)
    assert len(vars_list) == 2
    assert vars_list[0].sku != vars_list[1].sku
    assert len(vars_list[0].sku) <= 64
    assert len(vars_list[1].sku) <= 64
    assert any("LEOPARD" in v.sku for v in vars_list)
    assert any("ROZOV" in v.sku for v in vars_list)
