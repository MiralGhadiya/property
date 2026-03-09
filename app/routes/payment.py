# app/routes/payment.py

import os
import razorpay
from uuid import UUID
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from razorpay.errors import SignatureVerificationError
from fastapi import APIRouter, Depends, HTTPException, Request

from app.deps import get_db, get_current_user
from app.models import SubscriptionPlan, UserSubscription, User
from app.models.subscription_settings import SubscriptionSettings
from app.services.exchange_rate_service import get_rate


from app.utils.logger_config import app_logger as logger

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    logger.error("RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET is not set")
    raise RuntimeError("Missing RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET")

router = APIRouter(prefix="/payment", tags=["payment"])

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def _pricing_country(request: Request, current_user: User) -> str:
    ip_country = getattr(request.state, "ip_country", None)
    user_country = current_user.country.country_code
    return ip_country or user_country


def _expire_existing_active_subs(db: Session, user_id: int, now: datetime):
    db.query(UserSubscription).filter(
        UserSubscription.user_id == user_id,
        UserSubscription.is_active == True,
        UserSubscription.is_expired == False
    ).update({
        "is_active": False,
        "is_expired": True,
        "end_date": now
    })


@router.post("/create-order/{plan_id}")

def create_order(
    plan_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == plan_id,
        SubscriptionPlan.is_active == True
    ).first()

    if not plan:
        raise HTTPException(404, "Plan not found")
    
    pricing_country = _pricing_country(request, current_user)

    if plan.country_code == "DEFAULT":
        user_currency = current_user.country.currency_code
        rate = get_rate(db, user_currency)

        if not rate:
            raise HTTPException(400, "Currency not supported")

        amount = int(plan.price * rate * 100)
        currency = user_currency

    else:
        amount = int(plan.price * 100)
        currency = plan.currency

    existing_pending = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.plan_id == plan.id,
        UserSubscription.payment_status.in_(["CREATED", "PENDING"]),
        UserSubscription.is_active == False
    ).order_by(UserSubscription.id.desc()).first()
    
    if existing_pending:
        logger.info(
            f"[PAYMENT] Removing stale pending order "
            f"sub_id={existing_pending.id} "
            f"order_id={existing_pending.razorpay_order_id}"
        )
        existing_pending.payment_status = "EXPIRED"
        existing_pending.is_expired = True
        existing_pending.is_active = False
        db.commit()

    # if existing_pending:
    #     logger.info(
    #         f"[PAYMENT] Removing stale pending order "
    #         f"sub_id={existing_pending.id} "
    #         f"order_id={existing_pending.razorpay_order_id}"
    #     )
    #     try:
    #         db.delete(existing_pending)
    #         db.commit()
    #     except Exception:
    #         db.rollback()
    #         logger.exception("Failed to delete existing pending subscription")
    #         raise HTTPException(
    #             status_code=500,
    #             detail="Failed to reset previous pending payment"
    #         )

    # if existing_pending and existing_pending.razorpay_order_id:
    #     return {
    #         "order_id": existing_pending.razorpay_order_id,
    #         "razorpay_key": RAZORPAY_KEY_ID,
    #         "amount": amount,
    #         "currency": currency,
    #         # "amount": plan.price * 100,
    #         # "currency": plan.currency,
    #         "subscription_id": existing_pending.id
    #     }

    try:
        order = client.order.create({
            "amount": amount,
            "currency": currency,
            "payment_capture": 1,
        })

        sub = UserSubscription(
            user_id=current_user.id,
            plan_id=plan.id,
            pricing_country_code=pricing_country,
            ip_country_code=getattr(request.state, "ip_country", None),
            payment_country_code=pricing_country,
            razorpay_order_id=order["id"],
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
            "order_id": order["id"],
            "razorpay_key": RAZORPAY_KEY_ID,
            "amount": amount,
            # "currency": plan.currency,
            "currency": currency,
            "subscription_id": sub.id
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
        logger.exception("Unexpected error during order creation")
        raise HTTPException(500, "Unable to create payment order")

        
@router.post("/verify")
def verify_payment(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"],
        })

        sub = db.query(UserSubscription).filter(
            UserSubscription.razorpay_order_id == data["razorpay_order_id"],
            UserSubscription.user_id == current_user.id
        ).first()

        if not sub:
            raise HTTPException(404, "Subscription not found")

        if sub.payment_status == "PAID" and sub.is_active:
            return {"message": "Already activated",
                    "subscription_id": str(sub.id)
                    }

        # ✅ DEFINE NOW FIRST
        now = datetime.now(timezone.utc)

        # ✅ Expire old subscriptions
        # _expire_existing_active_subs(db, current_user.id, now)

        # ✅ ACTIVATE THIS SUBSCRIPTION
        sub.razorpay_payment_id = data["razorpay_payment_id"]
        sub.razorpay_signature = data["razorpay_signature"]
        sub.payment_status = "PAID"
        sub.is_active = True
        sub.is_expired = False
        sub.start_date = now
        # sub.end_date = now + relativedelta(years=2)
        
        settings = db.query(SubscriptionSettings).first()

        if not settings:
            raise HTTPException(500, "Subscription settings not configured")

        duration_days = settings.subscription_duration_days
        sub.end_date = now + relativedelta(days=duration_days)

        db.commit()

        return {
            "message": "Payment successful & subscription activated",
            "subscription_id": str(sub.id)
        }

    except SignatureVerificationError:
        raise HTTPException(400, "Invalid payment signature")