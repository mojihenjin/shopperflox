from unittest.mock import MagicMock, patch

import pytest
from fastapi import Response
from fastapi.testclient import TestClient

from main import app
from src.api.health import check_postgres, ready_service
from src.infrastructure.db import engine


@pytest.fixture(autouse=True)
def cleanup_db_engine():
    yield
    engine.sync_engine.dispose()


def test_health_live():
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.text == '"I\'m alive!"'


def test_health_ready_success():
    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["body"] == {"API": True, "postgres": True}
    assert data["errors"] == []


def test_health_ready_root_alias():
    client = TestClient(app)
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["body"] == {"API": True, "postgres": True}


def test_health_ready_when_postgres_unhealthy():
    client = TestClient(app)
    app.dependency_overrides[check_postgres] = lambda: False
    try:
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status_code"] == 503
        assert data["body"] == {"API": True, "postgres": False}
    finally:
        app.dependency_overrides.pop(check_postgres, None)


@pytest.mark.anyio
async def test_check_postgres_live():
    result = await check_postgres()
    assert result is True


@pytest.mark.anyio
async def test_check_postgres_failure():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("Connection refused")
    with patch("src.api.health.engine", mock_engine):
        result = await check_postgres()
        assert result is False


@pytest.mark.anyio
async def test_ready_service_direct_call():
    resp = Response()
    res = await ready_service(resp=resp, postgres_ready=False)
    assert resp.status_code == 503
    assert res.status_code == 503
    assert res.body == {"API": True, "postgres": False}

    resp_ok = Response()
    res_ok = await ready_service(resp=resp_ok, postgres_ready=True)
    assert resp_ok.status_code == 200
    assert res_ok.status_code == 200
    assert res_ok.body == {"API": True, "postgres": True}
