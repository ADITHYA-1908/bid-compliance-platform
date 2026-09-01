import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify backend root endpoint responds with success."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "BidVerify AI Backend is running"


def test_health_endpoint():
    """Verify service health endpoint responds with healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
