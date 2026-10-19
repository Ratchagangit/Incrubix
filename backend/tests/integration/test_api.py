"""Integration tests for IncuBrix FastAPI endpoints and middleware."""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestApiIntegration:
    def test_health_endpoint(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "app_name" in data

    def test_ready_endpoint(self):
        resp = client.get("/ready")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "checks" in data

    def test_correlation_id_middleware(self):
        # Client supplies correlation ID
        test_corr_id = str(uuid.uuid4())
        resp = client.get("/health", headers={"X-Correlation-Id": test_corr_id})
        assert resp.status_code == 200
        assert resp.headers.get("X-Correlation-Id") == test_corr_id

        # Server auto-generates if omitted
        resp2 = client.get("/health")
        assert "X-Correlation-Id" in resp2.headers

    def test_error_format_on_not_found(self):
        resp = client.get("/api/v1/videos/nonexistent-uuid-1234")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "retryable" in data["error"]
        assert "details" in data["error"]
        assert data["error"]["code"] == "VIDEO_NOT_FOUND"

    def test_idempotency_key_caching(self):
        # Test idempotency on an instruction post or upload
        idem_key = str(uuid.uuid4())
        # Non-existent project returns 404 error
        resp1 = client.post(
            "/api/v1/projects/dummy-project/instructions",
            json={"instruction": "Cut first 30 seconds"},
            headers={"Idempotency-Key": idem_key}
        )
        resp2 = client.post(
            "/api/v1/projects/dummy-project/instructions",
            json={"instruction": "Cut first 30 seconds"},
            headers={"Idempotency-Key": idem_key}
        )
        # Second call with same idempotency key returns identical status and cached body
        assert resp1.status_code == resp2.status_code
        assert resp1.json() == resp2.json()
