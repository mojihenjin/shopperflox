from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core import settings


def create_engine(url: str | None = None, **kwargs) -> AsyncEngine:
    db_url = url or settings.database_url
    engine_kwargs: dict = {
        "pool_pre_ping": True,
        "echo": settings.db_echo,
    }
    if "sqlite" not in db_url:
        pool_size = 30 if settings.enduro_attack else settings.db_pool_size
        max_overflow = 20 if settings.enduro_attack else settings.db_max_overflow
        engine_kwargs.update(
            {
                "pool_size": pool_size,
                "max_overflow": max_overflow,
            }
        )
    engine_kwargs.update(kwargs)
    return create_async_engine(db_url, **engine_kwargs)


def create_sessionmaker(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


engine = create_engine()
async_session_maker = create_sessionmaker(engine)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
