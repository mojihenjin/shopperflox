from decimal import Decimal

import pytest
from uuid6 import uuid7

from src.application.services import FavoriteService
from src.domain.exceptions import EntityNotFoundError
from src.domain.models import ProductDomain


@pytest.mark.anyio
async def test_favorite_lifecycle(catalog_uow):
    service = FavoriteService(catalog_uow)
    user_id = uuid7()
    cat_id = uuid7()

    # Create published product
    prod = ProductDomain(
        category_id=cat_id,
        title="Sneakers",
        slug="sneakers",
        base_price=Decimal("120.00"),
        is_published=True,
        created_by=user_id,
    )
    await catalog_uow.products.add(prod)

    # Add to favorites
    await service.add_favorite(user_id=user_id, product_id=prod.id)

    # Idempotent re-add
    await service.add_favorite(user_id=user_id, product_id=prod.id)

    # List favorites
    favs, total = await service.list_favorites(user_id=user_id)
    assert total == 1
    assert favs[0].id == prod.id

    # Remove from favorites
    await service.remove_favorite(user_id=user_id, product_id=prod.id)
    favs_after, total_after = await service.list_favorites(user_id=user_id)
    assert total_after == 0


@pytest.mark.anyio
async def test_favorite_non_existent_or_unpublished(catalog_uow):
    service = FavoriteService(catalog_uow)
    user_id = uuid7()

    # Non-existent product
    with pytest.raises(EntityNotFoundError):
        await service.add_favorite(user_id=user_id, product_id=uuid7())

    # Unpublished product
    unpub = ProductDomain(
        category_id=uuid7(),
        title="Draft",
        slug="draft",
        base_price=Decimal("10.00"),
        is_published=False,
        created_by=user_id,
    )
    await catalog_uow.products.add(unpub)

    with pytest.raises(EntityNotFoundError):
        await service.add_favorite(user_id=user_id, product_id=unpub.id)
