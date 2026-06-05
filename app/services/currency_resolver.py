# app/services/currency_resolver.py

from babel.numbers import get_territory_currencies

from app.services.exchange_rate_service import get_rate


def resolve_currency(db, country_code: str | None, profile_currency: str | None = None):
    """
    Resolve final currency + exchange rate.
    Priority:
    1️⃣ User profile currency
    2️⃣ Babel country → currency
    3️⃣ USD fallback
    """

    # 1️⃣ Use profile currency if available
    if profile_currency:
        rate = get_rate(db, profile_currency)
        if rate:
            return profile_currency, rate

    # 2️⃣ Resolve from country using Babel
    if country_code:
        try:
            currencies = get_territory_currencies(country_code)
            if currencies:
                currency = currencies[0]  # first official currency
                rate = get_rate(db, currency)
                if rate:
                    return currency, rate
        except Exception:
            pass

    # 3️⃣ Fallback
    return "USD", None
