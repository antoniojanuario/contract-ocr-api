"""
Unit tests for document upload endpoint
"""
import pytest
import io
from app.models.database import Document
from app.core.config import settings
from tests.conftest import TestingSessionLocal


def create_test_pdf_content() -> bytes:
    """Create a minimal valid PDF content for testing"""
    # This is a minimal PDF structure that should pass basic validation
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
300
%%EOF"""
    return pdf_content


def test_valid_pdf_upload(client):
    """
    Test valid PDF upload scenarios
    Requirements: 1.1, 1.2
    """
    # Create a valid PDF file
    pdf_content = create_test_pdf_content()
    
    # Test successful upload
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test_contract.pdf", io.BytesIO(pdf_content), "application/pdf")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "document_id" in data
    assert "status" in data
    assert "message" in data
    
    # Verify response values
    assert data["status"] == "queued"
    assert "uploaded successfully" in data["message"].lower()
    
    # Verify document ID is a valid UUID format
    import uuid
    try:
        uuid.UUID(data["document_id"])
    except ValueError:
        pytest.fail("document_id is not a valid UUID")
    
    # Verify database record was created
    db = TestingSessionLocal()
    try:
        document = db.query(Document).filter(Document.id == data["document_id"]).first()
        assert document is not None
        assert document.filename == "test_contract.pdf"
        assert document.status == "queued"
        assert document.file_size == len(pdf_content)
        assert document.progress == 0
    finally:
        db.close()


def test_file_size_limit_enforcement(client):
    """
    Test file size limit enforcement
    Requirements: 1.2, 1.3
    """
    # Create a file that exceeds the size limit
    max_size = settings.MAX_FILE_SIZE
    oversized_content = b"x" * (max_size + 1000)  # Exceed by 1000 bytes
    
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("large_contract.pdf", io.BytesIO(oversized_content), "application/pdf")}
    )
    
    assert response.status_code == 400
    data = response.json()
    
    # Verify error response structure
    assert "error" in data
    error = data["error"]
    assert "code" in error
    assert "message" in error
    assert "timestamp" in error
    
    # Verify error details
    assert error["code"] == "FILE_TOO_LARGE"
    assert "exceeds maximum" in error["message"].lower()
    
    # Verify details are provided
    if "details" in error:
        details = error["details"]
        assert "file_size" in details
        assert "max_size" in details
        assert details["file_size"] > details["max_size"]
    
    # Verify no new database record was created for this failed upload
    # (We can't check for zero count since other tests may have created records)
    # The error response already confirms the upload was rejected


def test_invalid_file_format_rejection(client):
    """
    Test invalid file format rejection
    Requirements: 1.3
    """
    # Test with a text file instead of PDF
    text_content = b"This is not a PDF file, just plain text content."
    
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("not_a_pdf.pdf", io.BytesIO(text_content), "text/plain")}
    )
    
    assert response.status_code == 400
    data = response.json()
    
    # Verify error response structure
    assert "error" in data
    error = data["error"]
    assert "code" in error
    assert "message" in error
    
    # Verify error details
    assert error["code"] in ["INVALID_FILE_FORMAT", "PDF_VALIDATION_ERROR"]
    assert "not a valid pdf" in error["message"].lower() or "pdf" in error["message"].lower()
    
    # Verify no new database record was created for this failed upload
    # (We can't check for zero count since other tests may have created records)
    # The error response already confirms the upload was rejected


def test_empty_file_rejection(client):
    """
    Test empty file rejection
    Requirements: 1.3
    """
    # Test with empty file
    empty_content = b""
    
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("empty.pdf", io.BytesIO(empty_content), "application/pdf")}
    )
    
    assert response.status_code == 400
    data = response.json()
    
    # Verify error response structure
    assert "error" in data
    error = data["error"]
    assert "code" in error
    assert "message" in error
    
    # Verify error details
    assert error["code"] == "EMPTY_FILE"
    assert "empty" in error["message"].lower()
    
    # Verify no new database record was created for this failed upload
    # (We can't check for zero count since other tests may have created records)
    # The error response already confirms the upload was rejected


def test_missing_file_parameter(client):
    """
    Test missing file parameter
    Requirements: 1.1
    """
    # Test without providing file parameter
    response = client.post("/api/v1/documents/upload")
    
    # FastAPI should return 422 for missing required parameter
    assert response.status_code == 422
    data = response.json()
    
    # Verify validation error structure
    assert "detail" in data
    # The detail should indicate missing file parameter
    assert any("file" in str(detail).lower() for detail in data["detail"])


def test_multiple_file_uploads(client):
    """
    Test multiple independent file uploads
    Requirements: 1.4
    """
    pdf_content1 = create_test_pdf_content()
    pdf_content2 = create_test_pdf_content()
    
    # Upload first file
    response1 = client.post(
        "/api/v1/documents/upload",
        files={"file": ("contract1.pdf", io.BytesIO(pdf_content1), "application/pdf")}
    )
    
    assert response1.status_code == 200
    data1 = response1.json()
    document_id1 = data1["document_id"]
    
    # Upload second file
    response2 = client.post(
        "/api/v1/documents/upload",
        files={"file": ("contract2.pdf", io.BytesIO(pdf_content2), "application/pdf")}
    )
    
    assert response2.status_code == 200
    data2 = response2.json()
    document_id2 = data2["document_id"]
    
    # Verify both uploads were successful and independent
    assert document_id1 != document_id2
    assert data1["status"] == "queued"
    assert data2["status"] == "queued"
    
    # Verify both database records exist
    db = TestingSessionLocal()
    try:
        document1 = db.query(Document).filter(Document.id == document_id1).first()
        document2 = db.query(Document).filter(Document.id == document_id2).first()
        
        assert document1 is not None
        assert document2 is not None
        assert document1.filename == "contract1.pdf"
        assert document2.filename == "contract2.pdf"
        assert document1.id != document2.id
    finally:
        db.close()


def test_status_endpoint(client):
    """
    Test document status endpoint
    Requirements: 8.1, 8.2
    """
    # First upload a document
    pdf_content = create_test_pdf_content()
    upload_response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test_contract.pdf", io.BytesIO(pdf_content), "application/pdf")}
    )
    
    assert upload_response.status_code == 200
    document_id = upload_response.json()["document_id"]
    
    # Test status endpoint
    status_response = client.get(f"/api/v1/documents/{document_id}/status")
    
    assert status_response.status_code == 200
    status_data = status_response.json()
    
    # Verify status response structure
    assert "document_id" in status_data
    assert "status" in status_data
    assert "progress" in status_data
    assert "message" in status_data
    
    # Verify status response values
    assert status_data["document_id"] == document_id
    assert status_data["status"] == "queued"
    assert status_data["progress"] == 0
    assert "queued" in status_data["message"].lower()


def test_invalid_document_id_status(client):
    """
    Test status endpoint with invalid document ID
    Requirements: 8.1
    """
    # Test with invalid UUID format
    response = client.get("/api/v1/documents/invalid-id/status")
    
    assert response.status_code == 400
    data = response.json()
    
    assert "error" in data
    error = data["error"]
    assert error["code"] == "INVALID_DOCUMENT_ID"
    assert "invalid document id" in error["message"].lower()


def test_nonexistent_document_status(client):
    """
    Test status endpoint with non-existent document ID
    Requirements: 8.1
    """
    # Test with valid UUID format but non-existent document
    import uuid
    fake_id = str(uuid.uuid4())
    
    response = client.get(f"/api/v1/documents/{fake_id}/status")
    
    assert response.status_code == 400
    data = response.json()
    
    assert "error" in data
    error = data["error"]
    assert error["code"] == "DOCUMENT_NOT_FOUND"
    assert "not found" in error["message"].lower()


def test_results_endpoint_not_completed(client):
    """
    Test results endpoint for non-completed document
    Requirements: 4.2
    """
    # First upload a document
    pdf_content = create_test_pdf_content()
    upload_response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test_contract.pdf", io.BytesIO(pdf_content), "application/pdf")}
    )
    
    assert upload_response.status_code == 200
    document_id = upload_response.json()["document_id"]
    
    # Test results endpoint (should fail since processing not completed)
    results_response = client.get(f"/api/v1/documents/{document_id}/results")
    
    assert results_response.status_code == 400
    data = results_response.json()
    
    assert "error" in data
    error = data["error"]
    assert error["code"] == "PROCESSING_NOT_COMPLETED"
    assert ("not completed" in error["message"].lower() or 
            "not available" in error["message"].lower())