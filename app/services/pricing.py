# app/services/pricing.py

from typing import Optional
from sqlalchemy.orm import Session

from app.models.subscription import SubscriptionPlan
from app.models.user import User
from app.services.currency_resolver import resolve_currency

from app.utils.logger_config import app_logger as logger


def resolve_pricing_country(request, current_user) -> str:
    if getattr(request.state, "ip_country", None):
        logger.debug(f"[Pricing] Using IP country: {request.state.ip_country}")
        return request.state.ip_country
    
    if current_user and current_user.country:
        logger.debug(f"[Pricing] Using user profile country: {current_user.country.country_code}")
        return current_user.country.country_code

    logger.debug("[Pricing] Falling back to DEFAULT country")
    return "DEFAULT"


def resolve_currency_code(request, current_user) -> str:
    if current_user and current_user.country and getattr(current_user.country, "currency_code", None):
        logger.debug(f"[Pricing] Using user currency: {current_user.country.currency_code}")
        return current_user.country.currency_code
    
    logger.debug("[Pricing] Falling back to USD currency")
    return "USD"


def get_plans_with_pricing(
    db: Session,
    country: str,
    current_user: Optional[User] = None,
    force_currency_by_country: bool = False
):
    logger.info(f"[Pricing] Fetching plans for country={country}, force_currency_by_country={force_currency_by_country}")

    # 1️⃣ Check if local country plans exist
    local_plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.country_code == country,
        SubscriptionPlan.is_active == True,
    ).order_by(SubscriptionPlan.price.asc()).all()

    logger.debug(f"[Pricing] Found {len(local_plans)} local plans")

    if local_plans:
        global_plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.country_code == "GLOBAL",
            SubscriptionPlan.is_active == True,
        ).first()

        logger.debug(f"[Pricing] Global plan exists: {bool(global_plan)}")

        response = list(local_plans)

        if global_plan:
            response.append(global_plan)

        logger.debug(f"[Pricing] Returning {len(response)} plans (local + global)")
        return response

    # 2️⃣ Fetch USD base plans (DEFAULT)
    usd_plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.country_code == "US",
        SubscriptionPlan.currency == "USD",
        SubscriptionPlan.is_active == True,
    ).order_by(SubscriptionPlan.price.asc()).all()

    logger.debug(f"[Pricing] Found {len(usd_plans)} USD base plans")

    # 3️⃣ Fetch GLOBAL plan
    global_plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.country_code == "GLOBAL",
        SubscriptionPlan.is_active == True,
    ).first()

    logger.debug(f"[Pricing] Global plan exists: {bool(global_plan)}")

    if not usd_plans and not global_plan:
        logger.debug("[Pricing] No plans found at all")
        return []

    # 4️⃣ Resolve currency + rate
    if force_currency_by_country:
        profile_currency = None
        logger.debug("[Pricing] Ignoring profile currency due to force flag")
    else:
        profile_currency = (
            current_user.country.currency_code
            if current_user and current_user.country and current_user.country.currency_code
            else None
        )
        logger.debug(f"[Pricing] Profile currency: {profile_currency}")

    user_currency, rate = resolve_currency(
        db=db,
        country_code=country,
        profile_currency=profile_currency
    )

    logger.debug(f"[Pricing] Resolved currency={user_currency}, rate={rate}")

    response = []

    # 5️⃣ Convert BASIC / PRO / MASTER
    for plan in usd_plans:
        converted_price = (
            round(plan.price * rate, 2)
            if rate is not None
            else plan.price
        )

        logger.debug(
            f"[Pricing] Plan={plan.name}, base_price={plan.price}, "
            f"converted_price={converted_price}, rate={rate}"
        )

        response.append({
            "id": plan.id,
            "name": plan.name,
            "price": converted_price,
            "currency": user_currency if rate else "USD",
            "converted": rate is not None,
            "base_price_usd": plan.price,
        })

    # 6️⃣ Add GLOBAL as-is (NO conversion)
    if global_plan:
        logger.debug(f"[Pricing] Adding GLOBAL plan without conversion: {global_plan.name}")

        response.append({
            "id": global_plan.id,
            "name": global_plan.name,
            "price": global_plan.price,
            "currency": global_plan.currency,
            "converted": False,
        })

    logger.debug(f"[Pricing] Final response count: {len(response)} plans")

    return response