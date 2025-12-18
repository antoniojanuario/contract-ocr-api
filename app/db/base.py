"""
Database base configuration
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Create database engine with fixed URL for Render compatibility
database_url = settings.database_url_fixed
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """Context manager to get database session for workers"""
    from contextlib import contextmanager
    
    @contextmanager
    def session_context():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    return session_context()