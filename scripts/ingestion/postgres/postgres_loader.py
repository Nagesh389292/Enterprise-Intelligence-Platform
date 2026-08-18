"""
PostgreSQL Connection Pool Manager using SQLAlchemy 2.0.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

def get_db_url() -> str:
    user = os.getenv("POSTGRES_USER", "nexacore_admin")
    password = os.getenv("POSTGRES_PASSWORD", "nexacore_secret_pass")
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5433")
    db = os.getenv("POSTGRES_DB", "nexacore_dw")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"

def get_engine():
    db_url = get_db_url()
    return create_engine(db_url, pool_size=5, max_overflow=10)

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
