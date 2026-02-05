"""
Database connection and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os

from database.models import Base, Transcript, SeedIndex

# Database URL from environment
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://sirna_user:sirna_pass_2024@localhost:5432/sirna_offtarget'
)

# Create engine
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

@contextmanager
def get_db_session() -> Session:
    """
    Context manager for database sessions
    
    Usage:
        with get_db_session() as session:
            results = session.query(Transcript).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def check_database_ready():
    """
    Check if database is initialized with transcriptome data
    
    Returns:
        (is_ready: bool, stats: dict)
    """
    try:
        with get_db_session() as session:
            transcript_count = session.query(Transcript).count()
            seed_count = session.query(SeedIndex).count()
            
            is_ready = transcript_count > 0 and seed_count > 0
            
            stats = {
                'transcripts': transcript_count,
                'seed_indices': seed_count,
                'status': 'ready' if is_ready else 'empty'
            }
            
            return is_ready, stats
    except Exception as e:
        return False, {'status': 'error', 'message': str(e)}
