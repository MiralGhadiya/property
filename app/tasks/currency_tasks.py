# app/tasks/currency_tasks.py

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from celery import shared_task

from app.models import ExchangeRate
from app.database.db import SessionLocal

from app.core.config_manager import get_config
from app.utils.logger_config import app_logger as logger

load_dotenv() 

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=60, retry_kwargs={"max_retries": 3})
def update_exchange_rates(self):
    # api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    api_key = get_config("EXCHANGE_RATE_API_KEY")
    if not api_key:
        raise RuntimeError("EXCHANGE_RATE_API_KEY not set")

    db = SessionLocal()
    try:
        res = requests.get(
            "https://api.exchangerate.host/live",
            params={"access_key": api_key, "base": "USD"},
            timeout=10,
        )
        res.raise_for_status()

        data = res.json()
        if not data.get("success"):
            raise RuntimeError(f"Exchange API failed: {data}")

        quotes = data.get("quotes")
        if not quotes:
            raise RuntimeError("No quotes found")

        for pair, rate in quotes.items():
            if not pair.startswith("USD"):
                continue

            currency = pair.replace("USD", "")

            existing = db.query(ExchangeRate).filter(
                ExchangeRate.currency_code == currency
            ).first()

            if existing:
                existing.rate_to_usd = rate
                existing.updated_at = datetime.utcnow()
            else:
                db.add(
                    ExchangeRate(
                        currency_code=currency,
                        rate_to_usd=rate,
                        updated_at=datetime.utcnow(),
                    )
                )
                
        db.commit()
        logger.info("Stored %s exchange rates", len(quotes))
        
    except Exception:
        db.rollback()
        logger.exception("Error updating exchange rates")
        raise

    finally:
        db.close()