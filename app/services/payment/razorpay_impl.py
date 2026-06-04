# app/services/payment/razorpay_impl.py

import razorpay
from sqlalchemy import or_
from sqlalchemy.orm import Session
from fastapi import HTTPException
from razorpay.errors import SignatureVerificationError

from app.core.config_manager import get_config
from app.models import SubscriptionPlan, UserSubscription
from app.services.payment.base import BasePaymentProvider
from app.utils.logger_config import app_logger as logger


def get_razorpay_client():
    key_id = get_config("RAZORPAY_KEY_ID")
    key_secret = get_config("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        raise RuntimeError("Missing Razorpay credentials")

    return razorpay.Client(auth=(key_id, key_secret))


class RazorpayProvider(BasePaymentProvider):
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
        try:
            client = get_razorpay_client()
            order = client.order.create({
                "amount": amount,
                "currency": currency,
                "payment_capture": 1,
            })

            sub = UserSubscription(
                user_id=user_id,
                plan_id=plan.id,
                pricing_country_code=pricing_country,
                ip_country_code=ip_country,
                payment_country_code=pricing_country,
                razorpay_order_id=order["id"],
                payment_provider="RAZORPAY",
                provider_order_id=order["id"],
                payment_status="PENDING",
                is_active=False,
                is_expired=False,
                start_date=None,
                end_date=None,
            )

            db.add(sub)
            db.commit()
            db.refresh(sub)

            return {
                "subscription_id": sub.id,
                "provider": "RAZORPAY",
                "order_id": order["id"],
                "amount": amount,
                "currency": currency,
                "razorpay_key": get_config("RAZORPAY_KEY_ID"),
                "checkout_payload": {
                    "razorpay_key": get_config("RAZORPAY_KEY_ID"),
                    "amount": amount,
                    "currency": currency,
                    "order_id": order["id"]
                }
            }

        except razorpay.errors.BadRequestError:
            db.rollback()
            logger.exception("Invalid Razorpay order request")
            raise HTTPException(400, "Invalid payment request")

        except razorpay.errors.ServerError:
            db.rollback()
            logger.exception("Razorpay server error")
            raise HTTPException(502, "Payment gateway unavailable")

        except Exception:
            db.rollback()
            logger.exception("Unexpected error during Razorpay order creation")
            raise HTTPException(500, "Unable to create payment order")

    def verify_payment(
        self,
        db: Session,
        payload: dict,
        user_id: str
    ) -> dict:
        try:
            client = get_razorpay_client()
            
            razorpay_order_id = payload.get("razorpay_order_id")
            razorpay_payment_id = payload.get("razorpay_payment_id")
            razorpay_signature = payload.get("razorpay_signature")
            
            if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
                raise HTTPException(400, "Missing required Razorpay verification parameters")

            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })

            sub = db.query(UserSubscription).filter(
                or_(
                    UserSubscription.provider_order_id == razorpay_order_id,
                    UserSubscription.razorpay_order_id == razorpay_order_id
                )
            ).first()

            if not sub:
                raise HTTPException(404, "Subscription not found")

            if str(sub.user_id) != str(user_id):
                raise HTTPException(403, "This subscription belongs to a different user")

            # Update provider tracking fields as well as legacy fields
            sub.razorpay_payment_id = razorpay_payment_id
            sub.razorpay_signature = razorpay_signature
            
            sub.provider_payment_id = razorpay_payment_id
            sub.provider_signature = razorpay_signature

            return {
                "subscription": sub,
                "payment_id": razorpay_payment_id
            }

        except SignatureVerificationError:
            raise HTTPException(400, "Invalid payment signature")
