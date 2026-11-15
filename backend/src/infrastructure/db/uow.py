from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .repositories import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyFavoriteRepository,
    SqlAlchemyProductImageRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyProductVariantRepository,
    SqlAlchemyUserAddressRepository,
    SqlAlchemyUserBanRepository,
    SqlAlchemyUserPersonalRepository,
    SqlAlchemyUserRepository,
)
from .session import async_session_maker


class SqlAlchemyUserUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_factory = session_factory or async_session_maker
        self._session: AsyncSession | None = None

        self.users: SqlAlchemyUserRepository
        self.personal: SqlAlchemyUserPersonalRepository
        self.addresses: SqlAlchemyUserAddressRepository
        self.bans: SqlAlchemyUserBanRepository

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.users = SqlAlchemyUserRepository(self._session)
        self.personal = SqlAlchemyUserPersonalRepository(self._session)
        self.addresses = SqlAlchemyUserAddressRepository(self._session)
        self.bans = SqlAlchemyUserBanRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            if self._session is not None:
                await self._session.close()
                self._session = None

    async def commit(self) -> None:
        if self._session is not None:
            await self._session.commit()

    async def rollback(self) -> None:
        if self._session is not None:
            await self._session.rollback()


class SqlAlchemyCatalogUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_factory = session_factory or async_session_maker
        self._session: AsyncSession | None = None

        self.categories: SqlAlchemyCategoryRepository
        self.products: SqlAlchemyProductRepository
        self.variants: SqlAlchemyProductVariantRepository
        self.images: SqlAlchemyProductImageRepository
        self.favorites: SqlAlchemyFavoriteRepository

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.categories = SqlAlchemyCategoryRepository(self._session)
        self.products = SqlAlchemyProductRepository(self._session)
        self.variants = SqlAlchemyProductVariantRepository(self._session)
        self.images = SqlAlchemyProductImageRepository(self._session)
        self.favorites = SqlAlchemyFavoriteRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            if self._session is not None:
                await self._session.close()
                self._session = None

    async def commit(self) -> None:
        if self._session is not None:
            await self._session.commit()

    async def rollback(self) -> None:
        if self._session is not None:
            await self._session.rollback()
