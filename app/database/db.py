# app/database.py
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.utils.logger_config import app_logger as logger

load_dotenv()


def build_database_url_from_env() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD", "")

    required_fields = {
        "POSTGRES_HOST": host,
        "POSTGRES_DB": db_name,
        "POSTGRES_USER": user,
    }
    missing_fields = [key for key, value in required_fields.items() if not value]
    if missing_fields:
        missing_text = ", ".join(missing_fields)
        raise RuntimeError(
            "DATABASE_URL is not set and the following database settings are missing: "
            f"{missing_text}"
        )

    encoded_password = quote_plus(password)
    return f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{db_name}"


DATABASE_URL = build_database_url_from_env()

logger.info("Initializing database engine")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
