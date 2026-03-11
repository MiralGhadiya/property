# app/auth.py

from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

from app.core.config_manager import get_config
from app.utils.logger_config import app_logger as logger


ACCESS_TOKEN_EXPIRE_DAYS = 7
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_secret_key():
    key = get_config("JWT_SECRET_KEY")

    if not key:
        logger.error("JWT_SECRET_KEY is not set")
        raise RuntimeError("SECRET_KEY is not set")

    return key


def get_algorithm():
    return get_config("ALGORITHM", "HS256")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(data: dict):
    secret = get_secret_key()
    algorithm = get_algorithm()

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "type": "access"
    })

    return jwt.encode(to_encode, secret, algorithm=algorithm)


def create_refresh_token(data: dict):
    secret = get_secret_key()
    algorithm = get_algorithm()

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })

    return jwt.encode(to_encode, secret, algorithm=algorithm)


def decode_token(token: str):
    if not token:
        return None
    
    try:
        secret = get_secret_key()
        algorithm = get_algorithm()

        return jwt.decode(token, secret, algorithms=[algorithm])

    except JWTError:
        logger.warning("JWT decode failed")
        return None