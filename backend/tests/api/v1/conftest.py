import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from main import app
from src.api.dependencies import get_token_blacklist, get_user_uow
from src.infrastructure.db.models import Base
from src.infrastructure.db.session import create_sessionmaker
from src.infrastructure.db.uow import SqlAlchemyUserUnitOfWork


class InMemoryTokenBlacklist:
    def __init__(self) -> None:
        self.revoked: set[str] = set()

    async def is_revoked(self, jti: str) -> bool:
        return jti in self.revoked

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        self.revoked.add(jti)


@pytest.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = create_sessionmaker(engine)
    blacklist = InMemoryTokenBlacklist()

    def _get_test_uow():
        return SqlAlchemyUserUnitOfWork(session_factory=factory)

    app.dependency_overrides[get_user_uow] = _get_test_uow
    app.dependency_overrides[get_token_blacklist] = lambda: blacklist

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_user_uow, None)
    app.dependency_overrides.pop(get_token_blacklist, None)
    await engine.dispose()
