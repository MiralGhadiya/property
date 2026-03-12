# app/core/config_manager.py

import time
from threading import Thread
from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.models.system_config import SystemConfig
from app.utils.logger_config import app_logger as logger

_config_cache = {}
_last_updated = None


def load_config():
    global _config_cache, _last_updated

    db: Session = SessionLocal()

    try:
        configs = db.query(SystemConfig).all()

        _config_cache = {c.config_key: c.config_value for c in configs}

        if configs:
            _last_updated = max(c.updated_at for c in configs if c.updated_at)

        logger.info(f"Loaded {len(_config_cache)} configs")

    finally:
        db.close()


def get_config(key: str, default=None):
    return _config_cache.get(key, default)


def check_for_updates():
    global _last_updated

    db: Session = SessionLocal()

    try:
        latest = db.query(SystemConfig)\
                   .order_by(SystemConfig.updated_at.desc())\
                   .first()

        if latest and (_last_updated is None or latest.updated_at > _last_updated):
            logger.info("Config change detected. Reloading...")
            load_config()

    finally:
        db.close()


def auto_reload(interval=10):
    """
    Check DB every X seconds for config updates
    """
    
    logger.info(f"Starting config auto-reload every {interval} seconds")

    def watcher():
        logger.info("Config watcher thread started")
        while True:
            try:
                check_for_updates()
            except Exception as e:
                logger.error(f"Config reload error: {e}")

            time.sleep(interval)

    Thread(target=watcher, daemon=True).start()