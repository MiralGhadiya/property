# app/models/subscription_settings.py

from sqlalchemy import Column, Integer

from app.database.db import Base


class SubscriptionSettings(Base):
    __tablename__ = "subscription_settings"

    id = Column(Integer, primary_key=True, default=1)
    subscription_duration_days = Column(Integer, nullable=False, default=730)
