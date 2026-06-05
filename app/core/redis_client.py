# app/core/redis_client.py

import os
import socket
from urllib.parse import urlparse, urlunparse

import redis
from dotenv import load_dotenv

from app.utils.logger_config import app_logger as logger

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# If REDIS_URL uses 'redis' as hostname, check if it's resolvable.
# If not resolvable (e.g. running on local Windows host), swap with '127.0.0.1'
try:
    parsed = urlparse(REDIS_URL)
    if parsed.hostname == "redis":
        try:
            socket.getaddrinfo("redis", None)
        except socket.gaierror:
            # Swap 'redis' hostname with '127.0.0.1'
            netloc = f"127.0.0.1:{parsed.port or 6379}"
            if parsed.username or parsed.password:
                auth = f"{parsed.username or ''}:{parsed.password or ''}@"
                netloc = auth + netloc
            parsed = parsed._replace(netloc=netloc)
            REDIS_URL = urlunparse(parsed)
except Exception as exc:
    logger.warning("Redis hostname resolution failed, using REDIS_URL fallback", exc_info=True)

redis_client = redis.from_url(REDIS_URL, decode_responses=True)
