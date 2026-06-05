import logging

from redis import Redis

logger = logging.getLogger(__name__)

r = Redis(host="127.0.0.1", port=6379, db=0)

logger.info("celery queue length: %s", r.llen("celery"))
logger.info("celery keys: %s", r.keys("*"))
