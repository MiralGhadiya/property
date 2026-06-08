# app/services/payment/factory.py

from typing import Type

from app.services.payment.payoneer_impl import PayoneerProvider
from app.services.payment.paypal_impl import PayPalProvider
from app.services.payment.razorpay_impl import RazorpayProvider
from app.services.payment.base import BasePaymentProvider


class PaymentProviderFactory:
    _providers: dict[str, Type[BasePaymentProvider]] = {
        "RAZORPAY": RazorpayProvider,
        "PAYPAL": PayPalProvider,
        "PAYONEER": PayoneerProvider,
    }

    @classmethod
    def get_provider(cls, name: str) -> BasePaymentProvider:
        provider_cls = cls._providers.get(name.upper())
        if not provider_cls:
            raise ValueError(f"Unsupported payment provider: {name}")
        return provider_cls()
