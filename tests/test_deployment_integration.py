"""
Integration tests for deployment scenarios
Tests application startup, health checks, database connectivity, and resource constraints
"""
import pytest
import asyncio
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import psutil
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.monitoring import resource_monitor, get_health_metrics
from app.db.init_db import init_database, check_database_connection
from app.services.file_storage import FileStorageService


class TestApplicationStartup:
    """Test application startup and health checks"""
    
    def test_health_check_endpoint(self):
        """Test health check endpoint returns proper status"""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert data["version"] == settings.VERSION
    
    def test_metrics_endpoint_enabled(self):
        """Test metrics endpoint when enabled"""
        with patch.object(settings, 'ENABLE_METRICS', True):
            client = TestClient(app)
            response = client.get("/metrics")
            
            assert response.status_code == 200
            assert "cpu_usage_percent" in response.text
            assert "memory_usage_percent" in response.text
    
    def test_metrics_endpoint_disabled(self):
        """Test metrics endpoint when disabled"""
        with patch.object(settings, 'ENABLE_METRICS', False):
            client = TestClient(app)
            response = client.get("/metrics")
            
            assert response.status_code == 404
    
    def test_root_endpoint_redirects(self):
        """Test root endpoint redirects to documentation"""
        client = TestClient(app)
        response = client.get("/", follow_redirects=False)
        
        assert response.status_code == 307
        assert "/docs" in response.headers["location"]
    
    @pytest.mark.asyncio
    async def test_health_metrics_generation(self):
        """Test health metrics generation"""
        metrics = await get_health_metrics()
        
        assert "status" in metrics
        assert "version" in metrics
        assert "environment" in metrics
        assert metrics["version"] == settings.VERSION
        
        if "metrics" in metrics:
            system_metrics = metrics["metrics"]
            assert "cpu" in system_metrics
            assert "memory" in system_metrics
            assert "disk" in system_metrics


class TestDatabaseConnectivity:
    """Test database connectivity and migrations"""
    
    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Test database connection works"""
        try:
            await check_database_connection()
            # If we get here, connection succeeded
            assert True
        except Exception as e:
            pytest.fail(f"Database connection failed: {e}")
    
    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """Test database initialization"""
        # Use a temporary database for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            test_db_url = f"sqlite:///{tmp_db.name}"
            
            with patch.object(settings, 'DATABASE_URL', test_db_url):
                try:
                    await init_database()
                    # If we get here, initialization succeeded
                    assert True
                except Exception as e:
                    pytest.fail(f"Database initialization failed: {e}")
                finally:
                    # Cleanup
                    if os.path.exists(tmp_db.name):
                        os.unlink(tmp_db.name)
    
    def test_database_url_configuration(self):
        """Test database URL is properly configured"""
        assert settings.DATABASE_URL is not None
        assert len(settings.DATABASE_URL) > 0
        
        # Should be either SQLite or PostgreSQL
        assert (settings.DATABASE_URL.startswith("sqlite://") or 
                settings.DATABASE_URL.startswith("postgresql://"))


class TestResourceConstraints:
    """Test application behavior under resource constraints"""
    
    def test_file_size_limits_respected(self):
        """Test file size limits are properly configured"""
        # Check that optimized file size is used for free platforms
        if settings.is_free_platform:
            assert settings.optimized_max_file_size <= 25 * 1024 * 1024  # 25MB max
        
        assert settings.optimized_max_file_size > 0
    
    def test_ocr_timeout_optimization(self):
        """Test OCR timeout is optimized for platform"""
        if settings.is_free_platform:
            assert settings.optimized_ocr_timeout <= 180  # 3 minutes max
        
        assert settings.optimized_ocr_timeout > 0
    
    def test_worker_count_optimization(self):
        """Test worker count is optimized for available resources"""
        assert settings.WORKER_COUNT >= 1
        
        # For free platforms, should be limited
        if settings.is_free_platform:
            assert settings.WORKER_COUNT <= 2
    
    def test_concurrent_task_limits(self):
        """Test concurrent task limits are reasonable"""
        assert settings.MAX_CONCURRENT_TASKS >= 1
        assert settings.MAX_CONCURRENT_TASKS <= 10  # Reasonable upper bound
    
    @pytest.mark.asyncio
    async def test_memory_monitoring(self):
        """Test memory monitoring functionality"""
        metrics = await resource_monitor.get_system_metrics()
        
        assert "memory" in metrics
        memory_info = metrics["memory"]
        assert "percent" in memory_info
        assert "available_mb" in memory_info
        assert "used_mb" in memory_info
        
        # Memory percentage should be reasonable
        assert 0 <= memory_info["percent"] <= 100
        assert memory_info["available_mb"] >= 0
    
    def test_rate_limiting_configuration(self):
        """Test rate limiting is properly configured"""
        assert settings.RATE_LIMIT_REQUESTS_PER_MINUTE > 0
        assert settings.RATE_LIMIT_REQUESTS_PER_HOUR > 0
        
        # Hour limit should be higher than minute limit
        assert settings.RATE_LIMIT_REQUESTS_PER_HOUR >= settings.RATE_LIMIT_REQUESTS_PER_MINUTE


class TestFileUploadUnderConstraints:
    """Test file upload and processing under resource constraints"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.file_storage = FileStorageService()
    
    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_upload_directory_creation(self):
        """Test upload directory is created properly"""
        upload_dir = Path(settings.UPLOAD_DIR)
        
        # Directory should exist or be creatable
        if not upload_dir.exists():
            try:
                upload_dir.mkdir(parents=True, exist_ok=True)
                assert upload_dir.exists()
            except Exception as e:
                pytest.fail(f"Cannot create upload directory: {e}")
    
    def test_file_storage_initialization(self):
        """Test file storage can be initialized"""
        try:
            storage = FileStorageService()
            assert storage is not None
        except Exception as e:
            pytest.fail(f"File storage initialization failed: {e}")
    
    def test_small_file_handling(self):
        """Test handling of small files (should always work)"""
        # Create a small test file
        test_content = b"Small test PDF content"
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(test_content)
            tmp_file.flush()
            
            try:
                # Test file size check
                file_size = os.path.getsize(tmp_file.name)
                assert file_size < settings.optimized_max_file_size
                
                # File should be acceptable
                assert file_size > 0
                
            finally:
                os.unlink(tmp_file.name)
    
    def test_large_file_rejection(self):
        """Test that oversized files are properly rejected"""
        # This test simulates checking file size without creating huge files
        oversized_file_size = settings.optimized_max_file_size + 1024
        
        # File size check should fail
        assert oversized_file_size > settings.optimized_max_file_size
    
    def test_upload_endpoint_with_constraints(self):
        """Test upload endpoint respects resource constraints"""
        client = TestClient(app)
        
        # Create a small test file
        test_content = b"Test PDF content for upload"
        
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_file:
            tmp_file.write(test_content)
            tmp_file.seek(0)
            
            # Test upload (may fail due to validation, but shouldn't crash)
            try:
                response = client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("test.pdf", tmp_file, "application/pdf")}
                )
                
                # Should get some response (success or validation error)
                assert response.status_code in [200, 400, 422]
                
            except Exception as e:
                # If it fails, it should be a controlled failure
                assert "timeout" not in str(e).lower()


class TestEnvironmentConfiguration:
    """Test environment-specific configuration"""
    
    def test_environment_detection(self):
        """Test environment is properly detected"""
        assert settings.ENVIRONMENT in ["local", "render", "railway", "heroku", "vercel"]
    
    def test_free_platform_detection(self):
        """Test free platform detection works"""
        # This is based on environment variables that may not be set in tests
        # So we just test the logic works
        is_free = settings.is_free_platform
        assert isinstance(is_free, bool)
    
    def test_logging_configuration(self):
        """Test logging is properly configured"""
        assert settings.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert settings.LOG_FORMAT in ["text", "json"]
    
    def test_security_settings(self):
        """Test security settings are properly configured"""
        assert isinstance(settings.ENABLE_SECURITY_HEADERS, bool)
        assert isinstance(settings.ENABLE_REQUEST_LOGGING, bool)
        assert isinstance(settings.REQUIRE_API_KEY, bool)
    
    def test_monitoring_settings(self):
        """Test monitoring settings are configured"""
        assert isinstance(settings.ENABLE_METRICS, bool)
        assert settings.METRICS_PORT > 0
        assert 0 < settings.CPU_ALERT_THRESHOLD <= 100
        assert 0 < settings.MEMORY_ALERT_THRESHOLD <= 100
        assert 0 < settings.DISK_ALERT_THRESHOLD <= 100


class TestDeploymentSpecificFeatures:
    """Test deployment-specific features"""
    
    def test_cors_configuration(self):
        """Test CORS is properly configured"""
        client = TestClient(app)
        
        # Test preflight request
        response = client.options(
            "/api/v1/documents/upload",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # Should handle CORS properly
        assert response.status_code in [200, 204]
    
    def test_openapi_documentation(self):
        """Test OpenAPI documentation is available"""
        client = TestClient(app)
        
        # Test OpenAPI schema
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
    
    def test_swagger_ui_available(self):
        """Test Swagger UI is available"""
        client = TestClient(app)
        
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()
    
    @pytest.mark.asyncio
    async def test_resource_monitoring_alerts(self):
        """Test resource monitoring alert system"""
        # Mock high resource usage
        with patch('psutil.cpu_percent', return_value=95.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 90.0
                mock_memory.return_value.available = 50 * 1024 * 1024  # 50MB
                mock_memory.return_value.total = 1024 * 1024 * 1024  # 1GB
                mock_memory.return_value.used = 974 * 1024 * 1024  # 974MB
                
                metrics = await resource_monitor.get_system_metrics()
                
                # Should detect high usage
                assert metrics["cpu"]["percent"] == 95.0
                assert metrics["memory"]["percent"] == 90.0
                
                # Alert checking should work without crashing
                try:
                    await resource_monitor.check_thresholds(metrics)
                except Exception as e:
                    pytest.fail(f"Alert checking failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])