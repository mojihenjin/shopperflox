import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from src.infrastructure.db.models import Base
from src.infrastructure.db.session import create_sessionmaker
from src.infrastructure.db.uow import SqlAlchemyUserUnitOfWork


@pytest.fixture
async def test_session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = create_sessionmaker(engine)
    yield factory
    await engine.dispose()


@pytest.fixture
def uow(test_session_factory):
    return SqlAlchemyUserUnitOfWork(session_factory=test_session_factory)
