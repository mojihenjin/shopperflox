from fastapi.testclient import TestClient
from main import app
from src.core import (
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
)


def test_metrics_endpoint_returns_200():
    client = TestClient(app)
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text


def test_metrics_captures_templated_route():
    client = TestClient(app)

    before = http_requests_total.labels(
        method="GET", path="/health/live", status_code="200"
    )._value.get()

    response = client.get("/health/live")
    assert response.status_code == 200

    after = http_requests_total.labels(
        method="GET", path="/health/live", status_code="200"
    )._value.get()

    assert after == before + 1


def test_metrics_protects_cardinality_on_unmatched_route():
    client = TestClient(app)

    before = http_requests_total.labels(
        method="GET", path="unmatched", status_code="404"
    )._value.get()

    # Dynamic route that does not exist
    response = client.get("/random-unknown-path/550e8400-e29b-41d4-a716-446655440000")
    assert response.status_code == 404

    after = http_requests_total.labels(
        method="GET", path="unmatched", status_code="404"
    )._value.get()

    assert after == before + 1

    # Check metrics output contains path="unmatched" and NOT the raw UUID
    metrics_resp = client.get("/metrics")
    assert 'path="unmatched"' in metrics_resp.text
    assert "550e8400-e29b-41d4-a716-446655440000" not in metrics_resp.text


def test_metrics_excludes_metrics_path_itself():
    client = TestClient(app)

    client.get("/metrics")

    # Ensure no label has path="/metrics"
    metrics_resp = client.get("/metrics")
    assert 'path="/metrics"' not in metrics_resp.text


def test_in_progress_decrements_to_zero():
    client = TestClient(app)

    client.get("/health/ready")

    in_progress = http_requests_in_progress.labels(method="GET")._value.get()
    assert in_progress == 0


def test_metrics_captures_500_on_unhandled_exception():
    @app.get("/test-internal-error", include_in_schema=False)
    async def trigger_error():
        raise RuntimeError("Test server crash")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-internal-error")
    assert response.status_code == 500

    metrics_resp = client.get("/metrics")
    assert (
        'http_requests_total{method="GET",path="/test-internal-error",status_code="500"}'
        in metrics_resp.text
    )

    in_progress = http_requests_in_progress.labels(method="GET")._value.get()
    assert in_progress == 0
