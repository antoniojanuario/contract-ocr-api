"""
Tests for monitoring and status tracking endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.main import app
from app.models.database import Document
from app.models.schemas import ProcessingStatus
from app.db.base import get_db


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def db_session(test_db):
    """Create database session for testing"""
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_document(db_session: Session):
    """Create a sample document for testing"""
    document = Document(
        id=str(uuid.uuid4()),
        filename="test_document.pdf",
        file_size=1024 * 1024,
        status=ProcessingStatus.COMPLETED.value,
        progress=100,
        page_count=5,
        processing_time=30.5,
        ocr_confidence=0.92,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


def test_processing_history_endpoint(client: TestClient, sample_document: Document):
    """Test the processing history endpoint"""
    response = client.get("/api/v1/documents/history")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Should contain our sample document
    if data:  # Only check if there are documents
        doc = data[0]
        assert "document_id" in doc
        assert "filename" in doc
        assert "status" in doc
        assert "progress" in doc


def test_processing_history_with_filters(client: TestClient, sample_document: Document):
    """Test the processing history endpoint with filters"""
    # Test status filter
    response = client.get("/api/v1/documents/history?status=completed")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Test pagination
    response = client.get("/api/v1/documents/history?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10


def test_processing_history_invalid_status(client: TestClient):
    """Test processing history with invalid status filter"""
    response = client.get("/api/v1/documents/history?status=invalid")
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_STATUS_FILTER"


def test_document_metadata_endpoint(client: TestClient, sample_document: Document):
    """Test the document metadata endpoint"""
    response = client.get(f"/api/v1/documents/{sample_document.id}/metadata")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert data["document_id"] == sample_document.id
    assert data["filename"] == sample_document.filename
    assert data["status"] == sample_document.status
    assert data["progress"] == sample_document.progress
    assert "statistics" in data
    
    # Check statistics structure
    stats = data["statistics"]
    assert "total_pages_processed" in stats
    assert "total_text_blocks" in stats
    assert "file_size_mb" in stats


def test_document_metadata_not_found(client: TestClient):
    """Test document metadata endpoint with non-existent document"""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/documents/{fake_id}/metadata")
    
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_document_metadata_invalid_id(client: TestClient):
    """Test document metadata endpoint with invalid document ID"""
    response = client.get("/api/v1/documents/invalid-id/metadata")
    
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_DOCUMENT_ID"


def test_webhook_configuration(client: TestClient, sample_document: Document):
    """Test webhook configuration endpoint"""
    webhook_config = {
        "url": "https://example.com/webhook",
        "events": ["completed", "failed"]
    }
    
    response = client.post(
        f"/api/v1/documents/{sample_document.id}/webhook",
        json=webhook_config
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["document_id"] == sample_document.id
    assert data["webhook_configured"] is True
    assert data["webhook_url"] == webhook_config["url"]
    assert data["events"] == webhook_config["events"]


def test_webhook_configuration_missing_url(client: TestClient, sample_document: Document):
    """Test webhook configuration with missing URL"""
    webhook_config = {
        "events": ["completed"]
    }
    
    response = client.post(
        f"/api/v1/documents/{sample_document.id}/webhook",
        json=webhook_config
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "MISSING_WEBHOOK_URL"


def test_webhook_configuration_invalid_url(client: TestClient, sample_document: Document):
    """Test webhook configuration with invalid URL"""
    webhook_config = {
        "url": "invalid-url",
        "events": ["completed"]
    }
    
    response = client.post(
        f"/api/v1/documents/{sample_document.id}/webhook",
        json=webhook_config
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_WEBHOOK_URL"


def test_system_health_check(client: TestClient):
    """Test system health check endpoint"""
    response = client.get("/api/v1/documents/system/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "status" in data
    assert data["status"] in ["healthy", "unhealthy"]
    assert "timestamp" in data
    assert "version" in data
    assert "components" in data
    
    # Check components
    components = data["components"]
    assert "database" in components
    assert "task_queue" in components
    
    # Each component should have status
    for component in components.values():
        assert "status" in component
        assert component["status"] in ["healthy", "unhealthy"]


def test_existing_status_endpoint_still_works(client: TestClient, sample_document: Document):
    """Test that existing status endpoint still works"""
    response = client.get(f"/api/v1/documents/{sample_document.id}/status")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["document_id"] == sample_document.id
    assert data["status"] == sample_document.status
    assert data["progress"] == sample_document.progress


def test_existing_results_endpoint_still_works(client: TestClient, sample_document: Document):
    """Test that existing results endpoint still works"""
    response = client.get(f"/api/v1/documents/{sample_document.id}/results")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["document_id"] == sample_document.id
    assert data["status"] == sample_document.status
    assert "metadata" in data
    assert "pages" in data