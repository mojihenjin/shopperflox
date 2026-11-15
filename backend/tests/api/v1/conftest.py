from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from main import app
from src.api.dependencies import (
    get_cart_uow,
    get_catalog_uow,
    get_email_verification_store,
    get_file_storage,
    get_order_uow,
    get_payment_gateway,
    get_review_uow,
    get_task_queue,
    get_token_blacklist,
    get_user_uow,
)
from src.infrastructure.db.models import Base
from src.infrastructure.db.session import create_sessionmaker
from src.infrastructure.db.uow import (
    SqlAlchemyCartUnitOfWork,
    SqlAlchemyCatalogUnitOfWork,
    SqlAlchemyOrderUnitOfWork,
    SqlAlchemyReviewUnitOfWork,
    SqlAlchemyUserUnitOfWork,
)
from src.infrastructure.payments import StubPaymentGateway


class InMemoryTokenBlacklist:
    def __init__(self) -> None:
        self.revoked: set[str] = set()

    async def is_revoked(self, jti: str) -> bool:
        return jti in self.revoked

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        self.revoked.add(jti)


class InMemoryEmailVerificationStore:
    def __init__(self) -> None:
        self.cooldowns: set[str] = set()
        self.user_cooldowns: set[str] = set()
        self.sessions: dict[str, dict] = {}

    async def save_session(
        self, token: str, payload: dict, ttl_seconds: int = 600
    ) -> None:
        self.sessions[token] = dict(payload)

    async def get_session(self, token: str) -> dict | None:
        session = self.sessions.get(token)
        return dict(session) if session else None

    async def increment_attempts(self, token: str) -> int:
        session = self.sessions.get(token)
        if not session:
            return -1
        attempts = int(session.get("attempts", 0)) + 1
        session["attempts"] = attempts
        if attempts >= 5:
            self.sessions.pop(token, None)
            return 5
        return attempts

    async def delete_session(self, token: str) -> None:
        self.sessions.pop(token, None)

    async def check_and_set_cooldown(self, email: str, ttl_seconds: int = 60) -> bool:
        clean = email.strip().lower()
        if clean in self.cooldowns:
            return False
        self.cooldowns.add(clean)
        return True

    async def check_and_set_user_cooldown(
        self, user_id: UUID, ttl_seconds: int = 60
    ) -> bool:
        uid = str(user_id)
        if uid in self.user_cooldowns:
            return False
        self.user_cooldowns.add(uid)
        return True


class InMemoryTaskQueue:
    def __init__(self) -> None:
        self.sent_emails: list[tuple[str, str, str]] = []

    async def enqueue_email(self, to_email: str, subject: str, body_text: str) -> None:
        self.sent_emails.append((to_email, subject, body_text))


class InMemoryFileStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def upload_file(self, *, key: str, data: bytes, content_type: str) -> str:
        self.files[key] = data
        return f"/media/{key.lstrip('/')}"

    async def delete_file(self, *, key: str) -> None:
        self.files.pop(key, None)


@pytest.fixture
def test_email_store():
    return InMemoryEmailVerificationStore()


@pytest.fixture
def test_task_queue():
    return InMemoryTaskQueue()


@pytest.fixture
def test_file_storage():
    return InMemoryFileStorage()


@pytest.fixture
async def client(test_email_store, test_task_queue, test_file_storage):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = create_sessionmaker(engine)
    blacklist = InMemoryTokenBlacklist()
    payment_gw = StubPaymentGateway()

    def _get_test_uow():
        return SqlAlchemyUserUnitOfWork(session_factory=factory)

    def _get_test_catalog_uow():
        return SqlAlchemyCatalogUnitOfWork(session_factory=factory)

    def _get_test_cart_uow():
        return SqlAlchemyCartUnitOfWork(session_factory=factory)

    def _get_test_order_uow():
        return SqlAlchemyOrderUnitOfWork(session_factory=factory)

    def _get_test_review_uow():
        return SqlAlchemyReviewUnitOfWork(session_factory=factory)

    app.dependency_overrides[get_user_uow] = _get_test_uow
    app.dependency_overrides[get_catalog_uow] = _get_test_catalog_uow
    app.dependency_overrides[get_cart_uow] = _get_test_cart_uow
    app.dependency_overrides[get_order_uow] = _get_test_order_uow
    app.dependency_overrides[get_review_uow] = _get_test_review_uow
    app.dependency_overrides[get_token_blacklist] = lambda: blacklist
    app.dependency_overrides[get_email_verification_store] = lambda: test_email_store
    app.dependency_overrides[get_task_queue] = lambda: test_task_queue
    app.dependency_overrides[get_file_storage] = lambda: test_file_storage
    app.dependency_overrides[get_payment_gateway] = lambda: payment_gw

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_user_uow, None)
    app.dependency_overrides.pop(get_catalog_uow, None)
    app.dependency_overrides.pop(get_cart_uow, None)
    app.dependency_overrides.pop(get_order_uow, None)
    app.dependency_overrides.pop(get_review_uow, None)
    app.dependency_overrides.pop(get_token_blacklist, None)
    app.dependency_overrides.pop(get_email_verification_store, None)
    app.dependency_overrides.pop(get_task_queue, None)
    app.dependency_overrides.pop(get_file_storage, None)
    app.dependency_overrides.pop(get_payment_gateway, None)
    await engine.dispose()
