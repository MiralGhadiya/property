# subscription_tasks.py

from app.celery_app import celery_app
from app.database.db import SessionLocal
from app.services.subscription_service import (
    expire_subscriptions,
    send_expiry_reminders,
)


@celery_app.task(name="app.tasks.subscription_tasks.expire_subscriptions_task")
def expire_subscriptions_task():
    db = SessionLocal()
    try:
        return expire_subscriptions(db)
    finally:
        db.close()


@celery_app.task(name="app.tasks.subscription_tasks.send_expiry_reminders_task")
def send_expiry_reminders_task():
    db = SessionLocal()
    try:
        return send_expiry_reminders(db)
    finally:
        db.close()
