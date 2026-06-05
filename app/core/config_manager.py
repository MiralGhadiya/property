import os
import time
from threading import Lock, Thread

from sqlalchemy.orm import Session

from app.core.redis_client import redis_client
from app.database.db import SessionLocal
from app.models.system_config import SystemConfig
from app.utils.logger_config import app_logger as logger

CONFIG_HASH = "system_config"
CONFIG_CHANNEL = "config_update_channel"

_reload_lock = Lock()
_last_reload = 0


# -------------------------
# LOAD CONFIG (SAFE)
# -------------------------
def load_config():
    global _last_reload

    # prevent rapid reload
    now = time.time()
    if now - _last_reload < 5:
        logger.debug("Skipping config reload (rate-limited)")
        return

    if not _reload_lock.acquire(blocking=False):
        logger.debug("Config reload already in progress")
        return

    db: Session = SessionLocal()

    try:
        logger.info("Loading config from DB")

        configs = db.query(SystemConfig.config_key, SystemConfig.config_value).all()

        pipe = redis_client.pipeline()

        for key, value in configs:
            pipe.hset(CONFIG_HASH, key, value)

        pipe.execute()

        redis_client.set("system_config_last_updated", now)

        _last_reload = now

        logger.info(f"Loaded {len(configs)} configs into Redis")

    except Exception as e:
        logger.exception(f"Config load failed: {e}")

    finally:
        db.close()
        _reload_lock.release()


# -------------------------
# GET CONFIG (FAST)
# -------------------------
def get_config(key: str, default=None):
    try:
        value = redis_client.hget(CONFIG_HASH, key)

        if value is None:
            return os.getenv(key, default)

        return value

    except Exception as e:
        logger.exception(f"Redis read failed: {e}")
        return default


# -------------------------
# LISTENER (SAFE LOOP)
# -------------------------
def start_config_listener():
    logger.info("Starting config listener")

    pubsub = redis_client.pubsub()
    pubsub.subscribe(CONFIG_CHANNEL)

    while True:
        try:
            message = pubsub.get_message(timeout=5)

            if message and message["type"] == "message":
                logger.info("Config update received")
                load_config()

            time.sleep(1)  # 🔥 CRITICAL

        except Exception as e:
            logger.exception(f"Listener error: {e}")
            time.sleep(5)


# -------------------------
# THREAD STARTER
# -------------------------
def start_listener_thread():
    Thread(target=start_config_listener, daemon=True, name="config-listener").start()


# -------------------------
# NOTIFY
# -------------------------
def notify_config_update():
    redis_client.publish(CONFIG_CHANNEL, "reload")
