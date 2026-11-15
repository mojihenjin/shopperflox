from fastapi.testclient import TestClient

from main import app


def test_api_docs_endpoints():
    client = TestClient(app)

    # Swagger UI
    resp_docs = client.get("/api/docs")
    assert resp_docs.status_code == 200
    assert "swagger-ui" in resp_docs.text.lower()

    # OpenAPI schema
    resp_openapi = client.get("/api/openapi.json")
    assert resp_openapi.status_code == 200
    openapi_data = resp_openapi.json()
    assert openapi_data["openapi"].startswith("3.")
    assert "/api/v1/auth/login" in openapi_data["paths"]

    # ReDoc
    resp_redoc = client.get("/api/redoc")
    assert resp_redoc.status_code == 200
    assert "redoc" in resp_redoc.text.lower()


def test_api_root_redirects_to_docs():
    client = TestClient(app, follow_redirects=False)

    resp_api = client.get("/api")
    assert resp_api.status_code in (307, 302, 301)
    assert resp_api.headers["location"] == "/api/docs"

    resp_api_slash = client.get("/api/")
    assert resp_api_slash.status_code in (307, 302, 301)
    assert resp_api_slash.headers["location"] == "/api/docs"

    resp_docs_legacy = client.get("/docs")
    assert resp_docs_legacy.status_code in (307, 302, 301)
    assert resp_docs_legacy.headers["location"] == "/api/docs"
