"""
Database initialization with deployment optimization
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
from app.models.database import Base
import logging

logger = logging.getLogger(__name__)

# Create async engine with deployment optimizations
def create_optimized_engine():
    """Create database engine optimized for deployment environment"""
    if settings.DATABASE_URL.startswith("sqlite"):
        # For SQLite, use aiosqlite with optimizations
        engine = create_async_engine(
            settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
            echo=settings.DEBUG,
            future=True,
            pool_pre_ping=True,
            connect_args={
                "check_same_thread": False,
                "timeout": 20
            }
        )
    else:
        # For PostgreSQL, use asyncpg with connection pooling
        pool_size = 5 if settings.is_free_platform else 10
        max_overflow = 0 if settings.is_free_platform else 5
        
        engine = create_async_engine(
            settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
            echo=settings.DEBUG,
            future=True,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=30,
            pool_recycle=3600  # 1 hour
        )
    
    return engine

engine = create_optimized_engine()

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_connection():
    """Check database connectivity"""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


async def init_database():
    """Initialize database tables with error handling"""
    try:
        logger.info(f"Initializing database for environment: {settings.ENVIRONMENT}")
        
        # Check connection first
        await check_database_connection()
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
        
        # Verify tables were created
        await verify_database_schema()
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def verify_database_schema():
    """Verify database schema is correct"""
    try:
        async with AsyncSessionLocal() as session:
            # Test basic queries on each table
            from app.models.database import Document, Page, TextBlock
            
            # Check if tables exist by running simple queries
            result = await session.execute(text("SELECT COUNT(*) FROM documents"))
            doc_count = result.scalar()
            
            result = await session.execute(text("SELECT COUNT(*) FROM pages"))
            page_count = result.scalar()
            
            result = await session.execute(text("SELECT COUNT(*) FROM text_blocks"))
            block_count = result.scalar()
            
            logger.info(f"Database schema verified: {doc_count} documents, {page_count} pages, {block_count} text blocks")
            
    except Exception as e:
        logger.error(f"Database schema verification failed: {e}")
        raise


async def cleanup_old_data():
    """Cleanup old data to manage storage on free platforms"""
    if not settings.is_free_platform:
        return
    
    try:
        from datetime import datetime, timedelta
        from app.models.database import Document
        
        # Delete documents older than 7 days on free platforms
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        async with AsyncSessionLocal() as session:
            # This would be implemented with proper cascade deletes
            # For now, just log the cleanup intent
            logger.info(f"Cleanup: Would delete documents older than {cutoff_date}")
            
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")


# Legacy sync functions for backward compatibility
def create_tables():
    """Create all database tables (sync version)"""
    asyncio.run(init_database())


def init_db():
    """Initialize database (sync version)"""
    asyncio.run(init_database())


def check_db_connection():
    """Check database connection (sync version)"""
    try:
        asyncio.run(check_database_connection())
        return True
    except:
        return False


if __name__ == "__main__":
    # Allow running this script directly for database setup
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            asyncio.run(init_database())
        elif command == "check":
            try:
                asyncio.run(check_database_connection())
                print("Database connection OK")
            except Exception as e:
                print(f"Database connection failed: {e}")
                sys.exit(1)
        else:
            print("Usage: python -m app.db.init_db [init|check]")
            sys.exit(1)
    else:
        print("Usage: python -m app.db.init_db [init|check]")
        sys.exit(1)