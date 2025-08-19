"""
Database configuration and session management
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:Ayush%40123@localhost:5432/transcription_db")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=bool(os.getenv("DEBUG", False)),
    future=True
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()
metadata = MetaData()

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        # Import models to ensure they're registered
        from . import models
        
        # Create tables only if they don't exist (checkfirst=True is default)
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            print(f"Database initialization warning: {e}")
            # Tables might already exist, which is fine

async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()