from fastapi.testclient import TestClient
from pydantic import BaseModel

from main import app
from src.core import ResponseGenerator, Settings, setup_logging


def test_response_generator_length_calculation():
    # Only list, tuple, set have length counted
    resp_list = ResponseGenerator.answer(body=[1, 2, 3])
    assert resp_list.metadata["length"] == 3

    resp_tuple = ResponseGenerator.answer(body=(1, 2))
    assert resp_tuple.metadata["length"] == 2

    resp_set = ResponseGenerator.answer(body={"a", "b"})
    assert resp_set.metadata["length"] == 2

    # dict has length of keys
    resp_dict = ResponseGenerator.answer(body={"key": "value"})
    assert resp_dict.metadata["length"] == 1

    resp_str = ResponseGenerator.answer(body="string")
    assert resp_str.metadata["length"] == 0

    # None body stays None
    resp_none = ResponseGenerator.answer(body=None)
    assert resp_none.body is None
    assert resp_none.metadata["length"] == 0


def test_response_generator_metadata_immutability():
    original_meta = {"custom": "value"}
    resp = ResponseGenerator.answer(body=[1], metadata=original_meta)

    # original dict was not mutated
    assert "length" not in original_meta
    assert resp.metadata["custom"] == "value"
    assert resp.metadata["length"] == 1


def test_response_generator_json_error():
    json_resp = ResponseGenerator.json_error(
        status_code=400,
        errors=[{"detail": "Bad request"}],
    )

    assert json_resp.status_code == 400
    import json

    data = json.loads(json_resp.body.decode("utf-8"))
    assert data["status_code"] == 400
    assert data["body"] is None
    assert data["errors"] == [{"detail": "Bad request"}]
    assert data["metadata"] == {"length": 0}


def test_global_404_format_under_base_response():
    client = TestClient(app)
    response = client.get("/non-existent-api-path")

    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["body"] is None
    assert data["errors"] == [{"detail": "Not Found"}]
    assert "X-Process-Time" in response.headers


def test_global_422_format_under_base_response():
    class TestPayload(BaseModel):
        required_field: int

    @app.post("/test-validation", include_in_schema=False)
    async def endpoint_with_validation(payload: TestPayload):
        return {"val": payload.required_field}

    client = TestClient(app)
    response = client.post("/test-validation", json={"required_field": "not-an-int"})

    assert response.status_code == 422
    data = response.json()
    assert data["status_code"] == 422
    assert data["body"] is None
    assert len(data["errors"]) > 0
    assert "X-Process-Time" in response.headers


def test_global_500_format_under_base_response():
    @app.get("/test-unhandled-crash", include_in_schema=False)
    async def crash_endpoint():
        raise RuntimeError("Secret internal database connection failed!")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-unhandled-crash")

    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["body"] is None
    # No leak of internal exception message
    assert data["errors"] == [{"detail": "Internal server error"}]
    assert "Secret internal database connection failed!" not in response.text


def test_logging_setup_both_modes():
    dev_settings = Settings(log_level="DEBUG", log_json=False)
    setup_logging(dev_settings)

    prod_settings = Settings(log_level="INFO", log_json=True)
    setup_logging(prod_settings)

    # restore dev mode for remaining tests
    setup_logging(dev_settings)
