# app/models/subscription.py

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.database.mixins import UUIDPrimaryKeyMixin


class SubscriptionPlan(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "subscription_plans"

    __table_args__ = (
        UniqueConstraint(
            "name", "country_code", "price", "currency", "max_reports", name="uq_subscription_plan_unique"
        ),
        Index("ix_subscription_plans_country_active", "country_code", "is_active"),
    )

    name = Column(String, nullable=False)
    country_code = Column(String, nullable=False, index=True)

    price = Column(Integer, nullable=False)
    currency = Column(String, nullable=False)

    max_reports = Column(Integer, nullable=True)

    is_active = Column(Boolean, default=True)
    # duration_days = Column(Integer, nullable=False, default=730)

    created_at = Column(DateTime, default=datetime.utcnow)


class UserSubscription(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_subscriptions"
    __table_args__ = (
        Index(
            "ix_user_subscriptions_user_active_window",
            "user_id",
            "is_active",
            "is_expired",
            "start_date",
            "end_date",
        ),
        Index("ix_user_subscriptions_pricing_country_code", "pricing_country_code"),
        Index("ix_user_subscriptions_payment_status", "payment_status"),
        Index("ix_user_subscriptions_start_date", "start_date"),
        Index("ix_user_subscriptions_end_date", "end_date"),
        Index(
            "ix_user_subscriptions_active_expiry_window",
            "is_active",
            "is_expired",
            "end_date",
        ),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False, index=True)

    pricing_country_code = Column(String, nullable=False)
    ip_country_code = Column(String, nullable=True, index=True)
    payment_country_code = Column(String, nullable=True, index=True)

    razorpay_order_id = Column(String, nullable=True)
    razorpay_payment_id = Column(String, nullable=True)
    razorpay_signature = Column(String, nullable=True)
    payment_status = Column(String, default="CREATED")

    payment_provider = Column(String, nullable=True, index=True)
    provider_order_id = Column(String, nullable=True, index=True)
    provider_payment_id = Column(String, nullable=True, index=True)
    provider_signature = Column(String, nullable=True)

    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    reports_used = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_expired = Column(Boolean, default=False)

    auto_renew = Column(Boolean, default=False)
    cancelled_at = Column(DateTime, nullable=True)

    user = relationship("User", lazy="selectin")
    plan = relationship("SubscriptionPlan", lazy="selectin")
