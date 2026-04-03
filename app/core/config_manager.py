# app/core/config_manager.py
import os
import time
from threading import Thread
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError

from app.database.db import SessionLocal
from app.core.redis_client import redis_client
from app.models.system_config import SystemConfig
from app.utils.logger_config import app_logger as logger


CONFIG_HASH = "system_config"
CONFIG_CHANNEL = "config_update_channel"
_missing_table_logged = False
_redis_read_fallback_logged = False
_redis_write_fallback_logged = False


def _get_env_config(key: str, default=None):
    value = os.getenv(key)
    return value if value not in (None, "") else default


def _is_missing_system_config_table(error: Exception) -> bool:
    message = str(error).lower()
    return "system_config" in message and "does not exist" in message


def load_config():
    global _missing_table_logged, _redis_write_fallback_logged
    logger.info("Starting config load from database")

    db: Session = SessionLocal()

    try:
        configs = db.query(SystemConfig).all()
    except ProgrammingError as e:
        db.rollback()
        if _is_missing_system_config_table(e):
            if not _missing_table_logged:
                logger.warning(
                    "system_config table is missing; skipping DB-backed config load. "
                    "Run Alembic migrations to enable database config."
                )
                _missing_table_logged = True
            return
        logger.exception(f"Failed to load configs: {e}")
        return
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to load configs: {e}")
        return

    try:
        if not configs:
            logger.warning("No system configs found in database")

        pipe = redis_client.pipeline()

        for c in configs:
            pipe.hset(CONFIG_HASH, c.config_key, c.config_value)

        pipe.execute()

        redis_client.set(
            "system_config_last_updated",
            time.time()
        )

        logger.info(
            f"Loaded {len(configs)} configs into Redis cache"
        )

    except Exception as e:
        if not _redis_write_fallback_logged:
            logger.warning(
                "Redis is unavailable while caching configs; environment variable "
                f"fallback will be used. Error: {e}"
            )
            _redis_write_fallback_logged = True

    finally:
        db.close()
        logger.debug("Database session closed after config load")


def get_config(key: str, default=None):
    global _redis_read_fallback_logged
    try:
        value = redis_client.hget(CONFIG_HASH, key)

        if value is None:
            env_value = _get_env_config(key, default)
            logger.debug(f"Config key '{key}' not found in Redis, returning fallback")
            return env_value

        logger.debug(f"Config fetch: {key}={value}")
        return value

    except Exception as e:
        if not _redis_read_fallback_logged:
            logger.warning(
                "Redis config reads are unavailable; falling back to environment "
                f"variables. Error: {e}"
            )
            _redis_read_fallback_logged = True
        return _get_env_config(key, default)


def start_config_listener():
    logger.info("Initializing Redis config listener")

    try:
        pubsub = redis_client.pubsub()
        pubsub.subscribe(CONFIG_CHANNEL)

        logger.info(
            f"Subscribed to Redis channel '{CONFIG_CHANNEL}' for config updates"
        )

        for message in pubsub.listen():

            if message["type"] != "message":
                continue

            logger.info(
                f"Config update event received: {message['data']}"
            )

            load_config()

    except Exception as e:
        logger.warning(
            "Config listener disabled because Redis is unavailable or misconfigured. "
            f"Error: {e}"
        )


def start_listener_thread():
    logger.info("Starting config listener thread")

    def run():
        try:
            start_config_listener()
        except Exception as e:
            logger.exception(f"Config listener thread failed: {e}")

    Thread(
        target=run,
        daemon=True,
        name="config-listener-thread"
    ).start()

    logger.info("Config listener thread started successfully")


def notify_config_update():
    try:
        redis_client.publish(CONFIG_CHANNEL, "reload")

        logger.info(
            f"Published config reload event to Redis channel '{CONFIG_CHANNEL}'"
        )

    except Exception as e:
        logger.exception(f"Failed to publish config update event: {e}")
