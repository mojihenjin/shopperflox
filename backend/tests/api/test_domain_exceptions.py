from fastapi.testclient import TestClient

from main import app
from src.domain.exceptions import DomainValidationError, InvalidStateTransitionError


def test_api_handles_domain_validation_error():
    @app.get("/test-domain-validation-error", include_in_schema=False)
    async def trigger_validation_error():
        raise DomainValidationError("Invalid entity field value")

    client = TestClient(app)
    response = client.get("/test-domain-validation-error")

    assert response.status_code == 400
    data = response.json()
    assert data["status_code"] == 400
    assert data["body"] is None
    assert data["errors"] == [{"detail": "Invalid entity field value"}]
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
