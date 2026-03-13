# app/core/config_manager.py

import time
from threading import Thread
from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.core.redis_client import redis_client
from app.models.system_config import SystemConfig
from app.utils.logger_config import app_logger as logger


CONFIG_HASH = "system_config"
CONFIG_CHANNEL = "config_update_channel"


def load_config():
    logger.info("Starting config load from database")

    db: Session = SessionLocal()

    try:
        configs = db.query(SystemConfig).all()

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
        logger.exception(f"Failed to load configs: {e}")

    finally:
        db.close()
        logger.debug("Database session closed after config load")


def get_config(key: str, default=None):
    try:
        value = redis_client.hget(CONFIG_HASH, key)

        if value is None:
            logger.debug(f"Config key '{key}' not found, returning default")
            return default

        logger.debug(f"Config fetch: {key}={value}")
        return value

    except Exception as e:
        logger.exception(f"Redis config read failed for key={key}: {e}")
        return default


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
        logger.exception(f"Config listener crashed: {e}")


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