from sqlalchemy.orm import Session

from app.models import ExchangeRate


def get_rate(db: Session, currency: str) -> float | None:
    rate = db.query(ExchangeRate).filter(ExchangeRate.currency_code == currency).first()
    return rate.rate_to_usd if rate else None
