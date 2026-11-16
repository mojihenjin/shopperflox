from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .repositories import (
    SqlAlchemyCartRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyFavoriteRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyOrderRepository,
    SqlAlchemyPaymentRepository,
    SqlAlchemyProductImageRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyProductVariantRepository,
    SqlAlchemyReviewRepository,
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


class SqlAlchemyCartUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_factory = session_factory or async_session_maker
        self._session: AsyncSession | None = None

        self.carts: SqlAlchemyCartRepository
        self.variants: SqlAlchemyProductVariantRepository
        self.products: SqlAlchemyProductRepository

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.carts = SqlAlchemyCartRepository(self._session)
        self.variants = SqlAlchemyProductVariantRepository(self._session)
        self.products = SqlAlchemyProductRepository(self._session)
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


class SqlAlchemyOrderUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_factory = session_factory or async_session_maker
        self._session: AsyncSession | None = None

        self.orders: SqlAlchemyOrderRepository
        self.carts: SqlAlchemyCartRepository
        self.variants: SqlAlchemyProductVariantRepository
        self.products: SqlAlchemyProductRepository
        self.addresses: SqlAlchemyUserAddressRepository
        self.payments: SqlAlchemyPaymentRepository

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.orders = SqlAlchemyOrderRepository(self._session)
        self.carts = SqlAlchemyCartRepository(self._session)
        self.variants = SqlAlchemyProductVariantRepository(self._session)
        self.products = SqlAlchemyProductRepository(self._session)
        self.addresses = SqlAlchemyUserAddressRepository(self._session)
        self.payments = SqlAlchemyPaymentRepository(self._session)
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


class SqlAlchemyReviewUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_factory = session_factory or async_session_maker
        self._session: AsyncSession | None = None

        self.reviews: SqlAlchemyReviewRepository
        self.orders: SqlAlchemyOrderRepository
        self.products: SqlAlchemyProductRepository

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.reviews = SqlAlchemyReviewRepository(self._session)
        self.orders = SqlAlchemyOrderRepository(self._session)
        self.products = SqlAlchemyProductRepository(self._session)
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


class SqlAlchemyNotificationUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_factory = session_factory or async_session_maker
        self._session: AsyncSession | None = None

        self.notifications: SqlAlchemyNotificationRepository
        self.users: SqlAlchemyUserRepository

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.notifications = SqlAlchemyNotificationRepository(self._session)
        self.users = SqlAlchemyUserRepository(self._session)
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
