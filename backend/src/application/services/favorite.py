from uuid import UUID

from src.domain.exceptions import EntityNotFoundError
from src.domain.interfaces import CatalogUnitOfWorkProtocol
from src.domain.models import FavoriteDomain, ProductDomain


class FavoriteService:
    def __init__(self, uow: CatalogUnitOfWorkProtocol) -> None:
        self.uow = uow

    async def add_favorite(self, *, user_id: UUID, product_id: UUID) -> None:
        async with self.uow:
            product = await self.uow.products.get_by_id(
                product_id, include_unpublished=False
            )
            if product is None or not product.is_available:
                raise EntityNotFoundError("Product not found or unavailable")

            already_exists = await self.uow.favorites.exists(user_id, product_id)
            if not already_exists:
                favorite = FavoriteDomain(
                    user_id=user_id,
                    product_id=product_id,
                    created_by=user_id,
                )
                await self.uow.favorites.add(favorite)
                await self.uow.commit()

    async def remove_favorite(self, *, user_id: UUID, product_id: UUID) -> None:
        async with self.uow:
            await self.uow.favorites.delete(user_id, product_id)
            await self.uow.commit()

    async def list_favorites(
        self, *, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[ProductDomain], int]:
        async with self.uow:
            return await self.uow.favorites.list_user_favorite_products(
                user_id, limit=limit, offset=offset
            )
