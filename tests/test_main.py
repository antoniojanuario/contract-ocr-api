"""
Test main application functionality
"""
import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_openapi_docs(client: TestClient):
    """Test OpenAPI documentation is accessible"""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200