# app/services/payment/base.py

from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from app.models import SubscriptionPlan

class BasePaymentProvider(ABC):
    @abstractmethod
    def create_order(
        self,
        db: Session,
        plan: SubscriptionPlan,
        amount: int,
        currency: str,
        user_id: str,
        pricing_country: str,
        ip_country: str | None
    ) -> dict:
        """Generates order on gateway, returns unified payload"""
        pass

    @abstractmethod
    def verify_payment(
        self,
        db: Session,
        payload: dict,
        user_id: str
    ) -> dict:
        """Captures/Verifies payment on gateway, returns activation details"""
        pass
