from fastapi.testclient import TestClient

from main import app
from src.domain.exceptions import (
    AuthenticationError,
    DomainError,
    DomainValidationError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    InvalidStateTransitionError,
    PermissionDeniedError,
)


def test_api_handles_domain_validation_error():
    @app.get("/test-domain-validation-error", include_in_schema=False)
    async def trigger_validation_error():
        raise DomainValidationError("Invalid entity field value")

    client = TestClient(app)
    response = client.get("/test-domain-validation-error")

    assert response.status_code == 422
    data = response.json()
    assert data["status_code"] == 422
    assert data["body"] is None
    assert data["errors"] == [{"detail": "Invalid entity field value"}]
    assert "X-Process-Time" in response.headers


def test_api_handles_generic_domain_error():
    @app.get("/test-generic-domain-error", include_in_schema=False)
    async def trigger_domain_error():
        raise DomainError("General domain rule violated")

    client = TestClient(app)
    response = client.get("/test-generic-domain-error")

    assert response.status_code == 400
    data = response.json()
    assert data["status_code"] == 400
    assert data["body"] is None
    assert data["errors"] == [{"detail": "General domain rule violated"}]
    assert "X-Process-Time" in response.headers


def test_api_handles_invalid_state_transition_error():
    @app.get("/test-invalid-state-transition-error", include_in_schema=False)
    async def trigger_state_transition_error():
        raise InvalidStateTransitionError("Cannot transition from CANCELLED to PAID")

    client = TestClient(app)
    response = client.get("/test-invalid-state-transition-error")

    assert response.status_code == 409
    data = response.json()
    assert data["status_code"] == 409
    assert data["body"] is None
    assert data["errors"] == [{"detail": "Cannot transition from CANCELLED to PAID"}]
    assert "X-Process-Time" in response.headers


def test_api_handles_authentication_error():
    @app.get("/test-authentication-error", include_in_schema=False)
    async def trigger_auth_error():
        raise AuthenticationError("Invalid login credentials")

    client = TestClient(app)
    response = client.get("/test-authentication-error")

    assert response.status_code == 401
    data = response.json()
    assert data["status_code"] == 401
    assert data["body"] is None
    assert data["errors"] == [{"detail": "Invalid login credentials"}]
    assert "X-Process-Time" in response.headers


def test_api_handles_permission_denied_error():
    @app.get("/test-permission-denied-error", include_in_schema=False)
    async def trigger_permission_error():
        raise PermissionDeniedError("Permission 'users:ban' required")

    client = TestClient(app)
    response = client.get("/test-permission-denied-error")

    assert response.status_code == 403
    data = response.json()
    assert data["status_code"] == 403
    assert data["body"] is None
    assert data["errors"] == [{"detail": "Permission 'users:ban' required"}]
    assert "X-Process-Time" in response.headers


def test_api_handles_entity_not_found_error():
    @app.get("/test-entity-not-found-error", include_in_schema=False)
    async def trigger_not_found_error():
        raise EntityNotFoundError("User with id 123 not found")

    client = TestClient(app)
    response = client.get("/test-entity-not-found-error")

    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["body"] is None
    assert data["errors"] == [{"detail": "User with id 123 not found"}]
    assert "X-Process-Time" in response.headers


def test_api_handles_entity_already_exists_error():
    @app.get("/test-entity-already-exists-error", include_in_schema=False)
    async def trigger_already_exists_error():
        raise EntityAlreadyExistsError("Login 'alice' already registered")

    client = TestClient(app)
    response = client.get("/test-entity-already-exists-error")

    assert response.status_code == 409
    data = response.json()
    assert data["status_code"] == 409
    assert data["body"] is None
    assert data["errors"] == [{"detail": "Login 'alice' already registered"}]
    assert "X-Process-Time" in response.headers
