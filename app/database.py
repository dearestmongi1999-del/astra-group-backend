from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings


engine: Engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.APP_DEBUG and settings.is_development,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Usage in routes:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_database_connection() -> dict:
    """
    Simple database connection test.

    Returns database name and user if connection is successful.
    Raises SQLAlchemyError if connection fails.
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT current_database() AS database_name, current_user AS database_user;")
            )
            row = result.mappings().first()

            if not row:
                return {
                    "connected": False,
                    "database": None,
                    "user": None,
                    "message": "No response returned from database.",
                }

            return {
                "connected": True,
                "database": row["database_name"],
                "user": row["database_user"],
                "message": "Database connected successfully.",
            }

    except SQLAlchemyError as exc:
        return {
            "connected": False,
            "database": None,
            "user": None,
            "message": str(exc),
        }
