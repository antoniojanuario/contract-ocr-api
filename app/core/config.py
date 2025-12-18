"""
Application configuration settings with deployment optimization
"""
import os
import psutil
from typing import List, Optional
from pydantic_settings import BaseSettings


def get_optimal_workers() -> int:
    """Calculate optimal number of workers based on available resources"""
    cpu_count = psutil.cpu_count()
    memory_gb = psutil.virtual_memory().total / (1024**3)
    
    # For free platforms with limited resources
    if memory_gb < 1:
        return 1
    elif memory_gb < 2:
        return min(2, cpu_count)
    else:
        return min(4, cpu_count * 2)


def get_deployment_environment() -> str:
    """Detect deployment environment"""
    if os.getenv("RENDER"):
        return "render"
    elif os.getenv("RAILWAY_ENVIRONMENT"):
        return "railway"
    elif os.getenv("HEROKU_APP_NAME"):
        return "heroku"
    elif os.getenv("VERCEL"):
        return "vercel"
    else:
        return "local"


class Settings(BaseSettings):
    # Application settings
    PROJECT_NAME: str = "Contract OCR API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment detection
    ENVIRONMENT: str = get_deployment_environment()
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # File upload settings - optimized for free platforms
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "52428800"))  # 50MB default, configurable
    MAX_PAGES: int = int(os.getenv("MAX_PAGES", "100"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    
    # Database settings with fallback
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./contract_ocr.db")
    
    # For Render PostgreSQL, convert postgres:// to postgresql://
    @property
    def database_url_fixed(self) -> str:
        """Fix database URL for SQLAlchemy compatibility"""
        if self.DATABASE_URL.startswith("postgres://"):
            return self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return self.DATABASE_URL
    
    # Redis settings (for task queue) with fallback to in-memory
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() == "true"
    
    # OCR settings - optimized for resource constraints
    OCR_CONFIDENCE_THRESHOLD: float = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.7"))
    OCR_TIMEOUT: int = int(os.getenv("OCR_TIMEOUT", "300"))  # 5 minutes default
    
    # Memory optimization
    MAX_CONCURRENT_TASKS: int = int(os.getenv("MAX_CONCURRENT_TASKS", "2"))
    MEMORY_LIMIT_MB: int = int(os.getenv("MEMORY_LIMIT_MB", "512"))
    
    # Worker settings
    WORKER_COUNT: int = int(os.getenv("WORKER_COUNT", str(get_optimal_workers())))
    WORKER_TIMEOUT: int = int(os.getenv("WORKER_TIMEOUT", "120"))
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json" if get_deployment_environment() != "local" else "text")
    
    # Authentication
    API_KEY_HEADER: str = "X-API-Key"
    REQUIRE_API_KEY: bool = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"
    
    # Rate limiting - adjusted for free platforms
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
    RATE_LIMIT_REQUESTS_PER_HOUR: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_HOUR", "1000"))
    
    # Security
    ENABLE_SECURITY_HEADERS: bool = os.getenv("ENABLE_SECURITY_HEADERS", "true").lower() == "true"
    ENABLE_REQUEST_LOGGING: bool = os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true"
    
    # Monitoring and alerting
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "9090"))
    ALERT_WEBHOOK_URL: Optional[str] = os.getenv("ALERT_WEBHOOK_URL")
    
    # Resource monitoring thresholds
    CPU_ALERT_THRESHOLD: float = float(os.getenv("CPU_ALERT_THRESHOLD", "80.0"))
    MEMORY_ALERT_THRESHOLD: float = float(os.getenv("MEMORY_ALERT_THRESHOLD", "85.0"))
    DISK_ALERT_THRESHOLD: float = float(os.getenv("DISK_ALERT_THRESHOLD", "90.0"))
    
    # Deployment-specific optimizations
    @property
    def is_free_platform(self) -> bool:
        """Check if running on a free platform with resource constraints"""
        return self.ENVIRONMENT in ["render", "railway", "heroku"]
    
    @property
    def optimized_max_file_size(self) -> int:
        """Get optimized file size based on platform"""
        if self.is_free_platform:
            return min(self.MAX_FILE_SIZE, 25 * 1024 * 1024)  # 25MB for free platforms
        return self.MAX_FILE_SIZE
    
    @property
    def optimized_ocr_timeout(self) -> int:
        """Get optimized OCR timeout based on platform"""
        if self.is_free_platform:
            return min(self.OCR_TIMEOUT, 180)  # 3 minutes for free platforms
        return self.OCR_TIMEOUT
    
    model_config = {"env_file": ".env"}


settings = Settings()