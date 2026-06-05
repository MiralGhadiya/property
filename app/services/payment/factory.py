# app/services/payment/factory.py

from app.services.payment.payoneer_impl import PayoneerProvider
from app.services.payment.paypal_impl import PayPalProvider
from app.services.payment.razorpay_impl import RazorpayProvider


class PaymentProviderFactory:
    _providers = {
        "RAZORPAY": RazorpayProvider,
        "PAYPAL": PayPalProvider,
        "PAYONEER": PayoneerProvider,
    }

    @classmethod
    def get_provider(cls, name: str):
        provider_cls = cls._providers.get(name.upper())
        if not provider_cls:
            raise ValueError(f"Unsupported payment provider: {name}")
        return provider_cls()
