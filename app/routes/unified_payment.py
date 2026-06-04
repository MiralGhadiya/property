# app/routes/unified_payment.py

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import SubscriptionPlan, UserSubscription, User
from app.models.subscription_settings import SubscriptionSettings
from app.services.exchange_rate_service import get_rate
from app.services.payment.factory import PaymentProviderFactory
from app.utils.logger_config import app_logger as logger

router = APIRouter(prefix="/payment/unified", tags=["payments"])


class UnifiedCreateOrderRequest(BaseModel):
    provider: str = Field(..., description="Payment provider name: RAZORPAY | PAYPAL | PAYONEER")


class UnifiedVerifyPaymentRequest(BaseModel):
    provider: str = Field(..., description="Payment provider name: RAZORPAY | PAYPAL | PAYONEER")

    # Flat parameters for premium flat structure
    razorpay_order_id: Optional[str] = Field(None, description="Razorpay Order ID")
    razorpay_payment_id: Optional[str] = Field(None, description="Razorpay Payment ID")
    razorpay_signature: Optional[str] = Field(None, description="Cryptographic signature from Razorpay")
    paypal_order_id: Optional[str] = Field(None, description="PayPal Sandbox/Live Order ID")
    payoneer_intent_id: Optional[str] = Field(None, description="Payoneer checkout intent ID")



def _pricing_country(request: Request, current_user: User) -> str:
    ip_country = getattr(request.state, "ip_country", None)
    user_country = current_user.country.country_code
    return ip_country or user_country


@router.post("/create-order/{plan_id}")
def create_unified_order(
    plan_id: UUID,
    body: UnifiedCreateOrderRequest,
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

    # Resolve pricing country and currency
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

    # Clean up stale pending orders
    existing_pending = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.plan_id == plan.id,
        UserSubscription.payment_provider == body.provider.upper(),
        UserSubscription.payment_status.in_(["CREATED", "PENDING"]),
        UserSubscription.is_active == False
    ).order_by(UserSubscription.id.desc()).first()

    if existing_pending:
        logger.info(
            f"[UNIFIED PAYMENT] Expiring stale pending order "
            f"sub_id={existing_pending.id} "
            f"order_id={existing_pending.provider_order_id}"
        )
        existing_pending.payment_status = "EXPIRED"
        existing_pending.is_expired = True
        existing_pending.is_active = False
        db.commit()

    try:
        # Resolve polymorphic provider subclass and execute
        provider = PaymentProviderFactory.get_provider(body.provider)
        response_data = provider.create_order(
            db=db,
            plan=plan,
            amount=amount,
            currency=currency,
            user_id=current_user.id,
            pricing_country=pricing_country,
            ip_country=getattr(request.state, "ip_country", None),
        )
        return response_data

    except ValueError as e:
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unified order creation failed")
        raise HTTPException(500, f"Unified payment failed: {str(e)}")





@router.post("/verify")
def verify_unified_payment(
    body: UnifiedVerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Resolve target payload dynamically for polymorphic providers
        target_payload = {}
        provider_upper = body.provider.upper()
        if provider_upper == "RAZORPAY":
            target_payload = {
                "razorpay_order_id": body.razorpay_order_id,
                "razorpay_payment_id": body.razorpay_payment_id,
                "razorpay_signature": body.razorpay_signature,
            }
        elif provider_upper == "PAYPAL":
            target_payload = {
                "paypal_order_id": body.paypal_order_id,
            }
        elif provider_upper == "PAYONEER":
            # Support both naming conventions for high robustness
            target_payload = {
                "payoneer_intent_id": body.payoneer_intent_id or body.paypal_order_id,
            }

        # Resolve polymorphic provider subclass and verify
        provider = PaymentProviderFactory.get_provider(body.provider)
        result = provider.verify_payment(
            db=db,
            payload=target_payload,
            user_id=current_user.id
        )

        sub = result["subscription"]

        if sub.payment_status == "PAID" and sub.is_active:
            return {
                "message": "Already activated",
                "subscription_id": str(sub.id)
            }

        # Activate subscription
        now = datetime.now(timezone.utc)
        sub.payment_status = "PAID"
        sub.is_active = True
        sub.is_expired = False
        sub.start_date = now

        # Compute dynamic duration
        settings = db.query(SubscriptionSettings).first()
        if not settings:
            settings = SubscriptionSettings(subscription_duration_days=365)
            db.add(settings)
            db.commit()
            db.refresh(settings)

        if not settings.subscription_duration_days or settings.subscription_duration_days <= 0:
            settings.subscription_duration_days = 365
            db.commit()
            db.refresh(settings)

        duration_days = settings.subscription_duration_days
        sub.end_date = now + relativedelta(days=duration_days)

        db.commit()

        return {
            "message": "Payment successful & subscription activated",
            "subscription_id": str(sub.id),
            "payment_id": result["payment_id"]
        }

    except ValueError as e:
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Unified payment verification failed")
        raise HTTPException(500, f"Verification failed: {str(e)}")


@router.get("/callback", response_class=HTMLResponse)
def payment_callback(status: str):
    is_success = status == "success"
    title_text = "Payment Authorized!" if is_success else "Payment Cancelled"
    description_text = (
        "You can now safely close this window and return to the main tab to verify."
        if is_success
        else "The payment flow was cancelled. You may close this window now."
    )
    status_color = "#FDB022" if is_success else "#FDA29B"
    bg_gradient = "linear-gradient(135deg, #003F32 0%, #00251E 100%)"

    return f"""
    <html>
        <head>
            <title>{title_text}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
            <style>
                body {{
                    font-family: 'Inter', sans-serif;
                    background: {bg_gradient};
                    color: white;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    padding: 20px;
                    box-sizing: border-box;
                }}
                .card {{
                    background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(20px);
                    -webkit-backdrop-filter: blur(20px);
                    padding: 48px 32px;
                    border-radius: 28px;
                    text-align: center;
                    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    max-width: 420px;
                    width: 100%;
                    animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
                }}
                @keyframes fadeInUp {{
                    from {{
                        opacity: 0;
                        transform: translateY(20px);
                    }}
                    to {{
                        opacity: 1;
                        transform: translateY(0);
                    }}
                }}
                .icon-container {{
                    width: 72px;
                    height: 72px;
                    background: rgba(255, 255, 255, 0.08);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 24px;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                }}
                .icon {{
                    width: 32px;
                    height: 32px;
                    color: {status_color};
                }}
                h1 {{
                    font-family: 'Outfit', sans-serif;
                    color: white;
                    font-size: 28px;
                    font-weight: 800;
                    margin: 0 0 12px;
                    letter-spacing: -0.5px;
                }}
                p {{
                    font-size: 15px;
                    color: #94A3B8;
                    line-height: 1.6;
                    margin: 0 0 32px;
                }}
                .btn {{
                    background-color: #FDB022;
                    color: #003F32;
                    border: none;
                    padding: 14px 28px;
                    border-radius: 14px;
                    font-family: 'Outfit', sans-serif;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    width: 100%;
                    box-shadow: 0 4px 14px rgba(253, 176, 34, 0.3);
                    transition: all 0.2s ease;
                }}
                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(253, 176, 34, 0.4);
                }}
                .btn:active {{
                    transform: translateY(0);
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="icon-container">
                    {'''<svg class="icon" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>''' if is_success else '''<svg class="icon" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>'''}
                </div>
                <h1>{title_text}</h1>
                <p>{description_text}</p>
                <button class="btn" onclick="window.close()">Close Window</button>
            </div>
            <script>
                // Automatically close the window after 2 seconds
                setTimeout(function() {{
                    window.close();
                }}, 2000);
            </script>
        </body>
    </html>
    """


