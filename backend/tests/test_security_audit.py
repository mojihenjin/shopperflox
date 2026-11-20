import io
from uuid import UUID

import pytest
from fastapi import UploadFile
from pydantic import ValidationError

from src.api.dependencies import get_user_uow
from src.api.utils import read_upload_with_limit
from src.api.v1.schemas import (
    BrandCreateRequest,
    ProductImageCreateRequest,
    QueueItemUpdateRequest,
)
from src.app.factory import create_app
from src.application.services import OrderService
from src.core import Settings
from src.domain.exceptions import DomainValidationError, PermissionDeniedError
from src.infrastructure.security import JwtTokenProvider
from tests.api.v1.conftest import (  # noqa: F401
    client,
    test_email_store,
    test_file_storage,
    test_task_queue,
)

pytestmark = pytest.mark.anyio


# ============================================================================
# 1. [FINDING-01] Иерархия привилегий и отзыв токенов при изменении прав
# ============================================================================


async def test_admin_privilege_escalation_forbidden(client):  # noqa: F811
    # 1. Register superadmin
    reg_super = await client.post(
        "/api/v1/auth/register",
        json={"login": "super_sec_probe", "password": "Password123!"},
    )
    super_id = UUID(reg_super.json()["body"]["user"]["id"])

    uow_factory = client._transport.app.dependency_overrides[get_user_uow]
    uow = uow_factory()
    async with uow:
        s_user = await uow.users.get_by_id(super_id)
        s_user.global_permissions = ["*"]
        await uow.users.update(s_user)
        await uow.commit()

    # 2. Register low-level operator
    reg_op = await client.post(
        "/api/v1/auth/register",
        json={"login": "operator_sec_probe", "password": "Password123!"},
    )
    op_id = UUID(reg_op.json()["body"]["user"]["id"])

    # Grant operator only "admin:access"
    async with uow:
        op_user = await uow.users.get_by_id(op_id)
        op_user.global_permissions = ["admin:access"]
        await uow.users.update(op_user)
        await uow.commit()

    # 3. Register victim user
    reg_victim = await client.post(
        "/api/v1/auth/register",
        json={"login": "victim_sec_probe", "password": "Password123!"},
    )
    victim_id = UUID(reg_victim.json()["body"]["user"]["id"])

    # Login as operator
    login_op = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "operator_sec_probe", "password": "Password123!"},
    )
    op_token = login_op.json()["body"]["access_token"]
    op_headers = {"Authorization": f"Bearer {op_token}"}

    # Operator attempts to grant "*" to themselves -> 403 Forbidden
    res_self_esc = await client.patch(
        f"/api/v1/admin/users/{op_id}",
        headers=op_headers,
        json={"global_permissions": ["*"]},
    )
    assert res_self_esc.status_code == 403
    assert "exceeding your own" in res_self_esc.json()["errors"][0]["detail"].lower()

    # Operator attempts to grant "*" to victim -> 403 Forbidden
    res_victim_esc = await client.patch(
        f"/api/v1/admin/users/{victim_id}",
        headers=op_headers,
        json={"global_permissions": ["*"]},
    )
    assert res_victim_esc.status_code == 403

    # Operator attempts to grant permissions they don't have (e.g. users:permissions) -> 403
    res_other_esc = await client.patch(
        f"/api/v1/admin/users/{victim_id}",
        headers=op_headers,
        json={"global_permissions": ["users:permissions"]},
    )
    assert res_other_esc.status_code == 403

    # Superadmin login
    login_super = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "super_sec_probe", "password": "Password123!"},
    )
    super_token = login_super.json()["body"]["access_token"]
    super_headers = {"Authorization": f"Bearer {super_token}"}

    # Superadmin can grant permissions successfully -> 200
    res_super_grant = await client.patch(
        f"/api/v1/admin/users/{victim_id}",
        headers=super_headers,
        json={"global_permissions": ["admin:access"]},
    )
    assert res_super_grant.status_code == 200
    assert "admin:access" in res_super_grant.json()["body"]["global_permissions"]


async def test_token_revocation_on_permission_change(client):  # noqa: F811
    # 1. Register superadmin and target user
    reg_super = await client.post(
        "/api/v1/auth/register",
        json={"login": "super_revoke_probe", "password": "Password123!"},
    )
    super_id = UUID(reg_super.json()["body"]["user"]["id"])

    uow_factory = client._transport.app.dependency_overrides[get_user_uow]
    uow = uow_factory()
    async with uow:
        s_user = await uow.users.get_by_id(super_id)
        s_user.global_permissions = ["*"]
        await uow.users.update(s_user)
        await uow.commit()

    reg_target = await client.post(
        "/api/v1/auth/register",
        json={"login": "target_revoke_probe", "password": "Password123!"},
    )
    target_id = UUID(reg_target.json()["body"]["user"]["id"])

    async with uow:
        t_user = await uow.users.get_by_id(target_id)
        t_user.global_permissions = ["admin:access"]
        await uow.users.update(t_user)
        await uow.commit()

    # Target user logs in and obtains token with admin:access
    login_target = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "target_revoke_probe", "password": "Password123!"},
    )
    old_target_token = login_target.json()["body"]["access_token"]
    old_target_headers = {"Authorization": f"Bearer {old_target_token}"}

    # Verify target can access admin endpoint
    check_ok = await client.get("/api/v1/admin/users", headers=old_target_headers)
    assert check_ok.status_code == 200

    # Superadmin logs in
    login_super = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "super_revoke_probe", "password": "Password123!"},
    )
    super_headers = {
        "Authorization": f"Bearer {login_super.json()['body']['access_token']}"
    }

    # Superadmin strips admin:access from target user
    demote_res = await client.patch(
        f"/api/v1/admin/users/{target_id}",
        headers=super_headers,
        json={"global_permissions": []},
    )
    assert demote_res.status_code == 200

    # Target user attempts to use old token -> must be rejected (revoked / no resurrected permissions)
    res_after_demote = await client.get(
        "/api/v1/admin/users", headers=old_target_headers
    )
    assert res_after_demote.status_code in (401, 403)


# ============================================================================
# 2. [FINDING-02] Запрет DEBUG=True в Production и защита debug_pay
# ============================================================================


def test_production_debug_forbidden_in_settings():
    # Production with debug=True must raise ValueError
    with pytest.raises(
        ValueError, match="DEBUG must be set to False when APP_ENV is 'production'"
    ):
        Settings(
            app_env="production",
            debug=True,
            enduro_attack=False,
            webhook_secret="a" * 32,
            jwt_secret_key="b" * 32,
        )

    # Production with debug=False succeeds
    valid_prod = Settings(
        app_env="production",
        debug=False,
        enduro_attack=False,
        webhook_secret="a" * 32,
        jwt_secret_key="b" * 32,
    )
    assert valid_prod.app_env == "production"
    assert valid_prod.debug is False


async def test_debug_pay_disabled_in_production():
    order_service = OrderService(
        uow=None,  # type: ignore
        debug=True,
        billing_enabled=False,
        app_env="production",
    )
    with pytest.raises(PermissionDeniedError, match="Debug payment is disabled"):
        await order_service.debug_pay(actor=None, order_id=UUID(int=1))  # type: ignore


# ============================================================================
# 3. [FINDING-03] Отключение Swagger / ReDoc / OpenAPI в Production
# ============================================================================


def test_swagger_openapi_disabled_in_production():
    prod_settings = Settings(
        app_env="production",
        debug=False,
        enduro_attack=False,
        webhook_secret="a" * 32,
        jwt_secret_key="b" * 32,
    )
    prod_app = create_app(prod_settings)
    assert prod_app.docs_url is None
    assert prod_app.redoc_url is None
    assert prod_app.openapi_url is None

    dev_settings = Settings(app_env="dev", debug=True)
    dev_app = create_app(dev_settings)
    assert dev_app.docs_url == "/api/docs"
    assert dev_app.redoc_url == "/api/redoc"
    assert dev_app.openapi_url == "/api/openapi.json"


# ============================================================================
# 4. [FINDING-05] Строгая валидация URL-схем против Stored XSS (SafeUrl)
# ============================================================================


def test_xss_url_schemes_rejected_in_schemas():
    # BrandCreateRequest: his_url
    with pytest.raises(ValidationError):
        BrandCreateRequest(name="Test Brand", his_url="javascript:alert(1)")

    with pytest.raises(ValidationError):
        BrandCreateRequest(
            name="Test Brand", his_url="data:text/html,<script>alert(1)</script>"
        )

    with pytest.raises(ValidationError):
        BrandCreateRequest(name="Test Brand", his_url="vbscript:msgbox(1)")

    # Valid brand URL
    valid_brand = BrandCreateRequest(
        name="Test Brand", his_url="https://example.com/brand"
    )
    assert valid_brand.his_url == "https://example.com/brand"

    # QueueItemUpdateRequest: tracking_url
    with pytest.raises(ValidationError):
        QueueItemUpdateRequest(tracking_url="javascript:stealToken()")

    valid_queue = QueueItemUpdateRequest(tracking_url="https://cdek.ru/tracking?id=123")
    assert valid_queue.tracking_url == "https://cdek.ru/tracking?id=123"

    # ProductImageCreateRequest: url
    with pytest.raises(ValidationError):
        ProductImageCreateRequest(url="javascript:alert(document.cookie)")

    with pytest.raises(ValidationError):
        ProductImageCreateRequest(url="data:image/svg+xml,<svg onload=alert(1)>")

    # Valid media and http image URLs
    valid_media_img = ProductImageCreateRequest(url="/media/products/item1.png")
    assert valid_media_img.url == "/media/products/item1.png"

    valid_http_img = ProductImageCreateRequest(url="https://cdn.example.com/item1.png")
    assert valid_http_img.url == "https://cdn.example.com/item1.png"


async def test_xss_url_rejected_via_api(client):  # noqa: F811
    reg = await client.post(
        "/api/v1/auth/register",
        json={"login": "creator_probe", "password": "Password123!"},
    )
    creator_id = UUID(reg.json()["body"]["user"]["id"])

    uow_factory = client._transport.app.dependency_overrides[get_user_uow]
    uow = uow_factory()
    async with uow:
        user = await uow.users.get_by_id(creator_id)
        user.global_permissions = ["creator:brand"]
        await uow.users.update(user)
        await uow.commit()

    provider = JwtTokenProvider()
    token = provider.create_access_token(creator_id, ["creator:brand"])
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to create brand with javascript: his_url -> 422
    res = await client.post(
        "/api/v1/brands",
        headers=headers,
        json={"name": "XSS Brand", "his_url": "javascript:alert(1)"},
    )
    assert res.status_code == 422


# ============================================================================
# 5. [FINDING-06] Потоковое чтение загружаемых файлов с лимитом размера
# ============================================================================


async def test_read_upload_with_limit_streaming():
    chunk_count = 0

    class StreamingBytesIO(io.BytesIO):
        def read(self, size=-1):
            nonlocal chunk_count
            chunk_count += 1
            return super().read(size)

    # 6 MB of data (exceeds 5 MB limit)
    total_bytes = 6 * 1024 * 1024
    fake_data = b"X" * total_bytes
    stream = StreamingBytesIO(fake_data)

    upload_file = UploadFile(file=stream, filename="test_large.dat")

    with pytest.raises(DomainValidationError, match="File size exceeds 5 MB limit"):
        await read_upload_with_limit(upload_file, max_bytes=5 * 1024 * 1024)

    # Verify that stream was stopped early without reading the full 6 MB
    # At 64KB per chunk: 5MB / 64KB = 80 chunks. 6MB / 64KB = 96 chunks.
    # The read loop must have stopped at ~81 chunks and not read all 96 chunks.
    assert chunk_count <= 85
