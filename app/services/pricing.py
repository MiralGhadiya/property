# app/services/pricing.py

from typing import Optional
from sqlalchemy.orm import Session

from app.models.subscription import SubscriptionPlan
from app.models.user import User
from app.services.currency_resolver import resolve_currency

from app.utils.logger_config import app_logger as logger


def resolve_pricing_country(request, current_user) -> str:
    if getattr(request.state, "ip_country", None):
        return request.state.ip_country
    
    if current_user and current_user.country:
        return current_user.country.country_code

    return "DEFAULT"


def resolve_currency_code(request, current_user) -> str:
    # preferred: currency from user profile country
    if current_user.country and getattr(current_user.country, "currency_code", None):
        return current_user.country.currency_code
    return "USD"


def get_plans_with_pricing(
    db: Session,
    country: str,
    current_user: Optional[User] = None
):
    from sqlalchemy import case

    plans = db.query(SubscriptionPlan).filter(
        (
            (SubscriptionPlan.country_code == country) |
            (SubscriptionPlan.country_code == "GLOBAL")
        ),
        SubscriptionPlan.is_active == True,
    ).order_by(
        case(
            (SubscriptionPlan.country_code == country, 0),  # local first
            else_=1
        ),
        SubscriptionPlan.price.asc()
    ).all()

    if plans:
        return plans

    # fallback to DEFAULT (with conversion)
    usd_plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.country_code == "DEFAULT",
        SubscriptionPlan.currency == "USD",
        SubscriptionPlan.is_active == True,
    ).all()

    if not usd_plans:
        return []

    profile_currency = (
        current_user.country.currency_code
        if current_user and current_user.country and current_user.country.currency_code
        else None
    )

    user_currency, rate = resolve_currency(
        db=db,
        country_code=country,
        profile_currency=profile_currency
    )

    if rate is None:
        logger.warning(f"No exchange rate for currency={user_currency}")

    response = []
    for plan in usd_plans:
        converted_price = (
            round(plan.price * rate, 2)
            if rate is not None
            else plan.price
        )

        response.append({
            "id": plan.id,
            "name": plan.name,
            "price": converted_price,
            "currency": user_currency if rate else "USD",
            "converted": True,
            "base_price_usd": plan.price,
        })

    return response