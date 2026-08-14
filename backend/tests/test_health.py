"""
HospitalOps AI — Tests for /health endpoint.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Return a synchronous test client for the FastAPI app."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /api/v1/health"""

    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_correct_app_name(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        data = response.json()
        assert data["app_name"] == "HospitalOps AI"

    def test_health_returns_version(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.1.0"

    def test_health_returns_timestamp(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"] is not None

    def test_health_returns_chunk(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        data = response.json()
        assert "chunk" in data
        assert "0.1" in data["chunk"]

    def test_health_response_shape(self, client: TestClient) -> None:
        """Ensure all expected fields are present in the response."""
        response = client.get("/api/v1/health")
        data = response.json()
        required_fields = {"status", "app_name", "version", "timestamp", "chunk"}
        assert required_fields.issubset(data.keys())

    def test_health_content_type_is_json(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert "application/json" in response.headers["content-type"]


class TestOpenAPISpec:
    """Basic checks that OpenAPI spec is served correctly."""

    def test_openapi_json_served(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_docs_served(self, client: TestClient) -> None:
        response = client.get("/docs")
        assert response.status_code == 200
