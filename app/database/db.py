import os
from typing import Any
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.utils.logger_config import app_logger as logger

load_dotenv()


def get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}

def normalize_database_url(database_url: str) -> str:
    normalized_url = database_url.strip().strip('"').strip("'")

    if normalized_url.startswith("postgres://"):
        return normalized_url.replace(
            "postgres://",
            "postgresql+psycopg2://",
            1,
        )

    if (
        normalized_url.startswith("postgresql://")
        and "+psycopg2" not in normalized_url
    ):
        return normalized_url.replace(
            "postgresql://",
            "postgresql+psycopg2://",
            1,
        )

    return normalized_url


def build_database_url_from_parts() -> str | None:
    host = os.getenv("POSTGRES_HOST")
    database = os.getenv("POSTGRES_DB")
    username = os.getenv("POSTGRES_USER")

    if not all([host, database, username]):
        return None

    port = os.getenv("POSTGRES_PORT", "5432")
    password = os.getenv("POSTGRES_PASSWORD")
    auth = quote_plus(username)

    if password:
        auth = f"{auth}:{quote_plus(password)}"

    return f"postgresql+psycopg2://{auth}@{host}:{port}/{database}"


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL") or build_database_url_from_parts()

    if not database_url:
        raise RuntimeError(
            "Database configuration is missing. Set DATABASE_URL or the "
            "POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, and "
            "POSTGRES_PASSWORD environment variables."
        )

    return normalize_database_url(database_url)


def get_database_connect_args(database_url: str) -> dict[str, Any]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}

    connect_args: dict[str, Any] = {}
    sslmode = os.getenv("POSTGRES_SSLMODE")
    connect_timeout = os.getenv("POSTGRES_CONNECT_TIMEOUT")

    if sslmode:
        connect_args["sslmode"] = sslmode

    if connect_timeout:
        connect_args["connect_timeout"] = int(connect_timeout)

    return connect_args


def get_engine_options(database_url: str) -> dict[str, Any]:
    engine_options: dict[str, Any] = {}
    connect_args = get_database_connect_args(database_url)

    if connect_args:
        engine_options["connect_args"] = connect_args

    if database_url.startswith("sqlite"):
        return engine_options

    engine_options["pool_pre_ping"] = True
    engine_options["pool_size"] = int(os.getenv("DB_POOL_SIZE", "5"))
    engine_options["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    engine_options["pool_recycle"] = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    engine_options["pool_timeout"] = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    engine_options["pool_use_lifo"] = get_bool_env("DB_POOL_USE_LIFO", True)

    return engine_options


DATABASE_URL = get_database_url()

logger.info("Initializing database engine")

engine = create_engine(DATABASE_URL, **get_engine_options(DATABASE_URL))
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
