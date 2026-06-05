# app/models/exchange_rate.py

from datetime import datetime

from sqlalchemy import Column, DateTime, Numeric, String

from app.database.db import Base
from app.database.mixins import UUIDPrimaryKeyMixin


class ExchangeRate(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "exchange_rates"

    currency_code = Column(String(3), unique=True, nullable=False)
    rate_to_usd = Column(Numeric(18, 6), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
