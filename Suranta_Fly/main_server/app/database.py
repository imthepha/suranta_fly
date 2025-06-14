from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
from tenacity import retry, stop_after_attempt, wait_exponential
from .core.config import settings
from .core.logger import get_logger

# Configure logging
logger = get_logger(__name__)

# Database URL from settings
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create engine with connection pooling and optimization settings
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,  # Use QueuePool for connection pooling
    pool_pre_ping=True,   # Enable connection health checks
    pool_size=5,          # Number of permanent connections
    max_overflow=10,      # Maximum number of connections that can be created beyond pool_size
    pool_timeout=30,      # Seconds to wait before giving up on getting a connection
    pool_recycle=1800,    # Recycle connections after 30 minutes
    pool_use_lifo=True,   # Use LIFO for connection reuse
    pool_reset_on_return='rollback',  # Reset connection state on return
    connect_args={
        'connect_timeout': 10,
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5
    },
    echo=settings.SQL_ECHO,  # Enable SQL query logging in debug mode
)

# Configure session factory with optimized settings
SessionLocal = sessionmaker(
    autocommit=False,     # Don't autocommit changes
    autoflush=False,      # Don't autoflush changes
    bind=engine,          # Bind to our engine
    expire_on_commit=False  # Don't expire objects on commit
)

# Create declarative base for models
Base = declarative_base()

# Event listeners for connection tracking and debugging
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    """Log when a new database connection is created."""
    logger.debug("New database connection created")

@event.listens_for(engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool."""
    logger.debug("Database connection checked out from pool")

@event.listens_for(engine, "checkin")
def checkin(dbapi_connection, connection_record):
    """Log when a connection is returned to the pool."""
    logger.debug("Database connection returned to pool")

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with retry logic and proper cleanup.
    Adapt this to your project's database access method.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
        logger.debug("Database session closed")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency with retry logic for database sessions.
    Adapt this to your project's dependency injection system.
    """
    with get_db() as db:
        try:
            yield db
        except Exception as e:
            logger.error(f"Database session error in FastAPI dependency: {str(e)}")
            raise

def init_db():
    """
    Initialize the database by creating all tables.
    
    This function creates all database tables defined in the models.
    It should be called during application startup.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise

def get_engine():
    """
    Get the database engine instance.
    
    This function is useful for database migrations and other operations
    that need direct access to the engine.
    
    Returns:
        Engine: SQLAlchemy engine instance
    """
    return engine 