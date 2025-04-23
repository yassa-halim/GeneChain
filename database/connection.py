from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from config import DATABASE_URL
from contextlib import contextmanager
from dotenv import load_dotenv
import os
import logging

load_dotenv()

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@contextmanager
def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

get_db = contextmanager(get_session)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def drop_db():
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database dropped successfully.")
    except Exception as e:
        logger.error(f"Error dropping database: {str(e)}")
        raise

def reset_db():
    try:
        drop_db()
        init_db()
        logger.info("Database reset successfully.")
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        raise

def get_db_url():
    db_url = os.getenv('DATABASE_URL', None)
    if db_url is None:
        logger.warning("DATABASE_URL is not set in the environment variables.")
    return db_url

def test_db_connection():
    try:
        with get_db() as db:
            db.execute("SELECT 1")
        logger.info("Database connection successful.")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise

def close_db_connection():
    try:
        engine.dispose()
        logger.info("Database connection closed successfully.")
    except Exception as e:
        logger.error(f"Error closing database connection: {str(e)}")
        raise
