# app/services/payment/paypal_impl.py

import requests
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config_manager import get_config
from app.models import SubscriptionPlan, UserSubscription
from app.services.payment.base import BasePaymentProvider
from app.utils.logger_config import app_logger as logger


def get_paypal_config():
    client_id = get_config("PAYPAL_CLIENT_ID")
    client_secret = get_config("PAYPAL_CLIENT_SECRET")
    mode = get_config("PAYPAL_MODE") or "sandbox"

    if not client_id or not client_secret:
        raise RuntimeError("Missing PayPal credentials")

    base_url = "https://api-m.paypal.com" if mode.lower() == "live" else "https://api-m.sandbox.paypal.com"
    return client_id, client_secret, base_url


def get_paypal_access_token() -> str:
    client_id, client_secret, base_url = get_paypal_config()

    try:
        response = requests.post(
            f"{base_url}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json", "Accept-Language": "en_US"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception:
        logger.exception("Failed to obtain PayPal access token")
        raise HTTPException(502, "Failed to authenticate with PayPal gateway")


class PayPalProvider(BasePaymentProvider):
    def create_order(
        self,
        db: Session,
        plan: SubscriptionPlan,
        amount: int,
        currency: str,
        user_id: str,
        pricing_country: str,
        ip_country: str | None,
    ) -> dict:
        _, _, base_url = get_paypal_config()
        token = get_paypal_access_token()

        # PayPal uses standard units with decimals (e.g. 29.00) instead of subunit cents (e.g. 2900)
        formatted_amount = f"{amount / 100:.2f}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Prefer": "return=representation",
        }

        base_api_url = get_config("BASE_URL") or "https://api.desktopvaluation.in"
        base_api_url = base_api_url.rstrip("/")
        return_url = f"{base_api_url}/payment/unified/callback?status=success"
        cancel_url = f"{base_api_url}/payment/unified/callback?status=cancel"

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {"currency_code": currency.upper(), "value": formatted_amount},
                    "description": f"Desktop Valuation Plan: {plan.name}",
                }
            ],
            "application_context": {
                "return_url": return_url,
                "cancel_url": cancel_url,
                "brand_name": "Desktop Valuation",
                "user_action": "PAY_NOW",
            },
        }

        try:
            response = requests.post(f"{base_url}/v2/checkout/orders", json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            order_data = response.json()
            order_id = order_data["id"]

            sub = UserSubscription(
                user_id=user_id,
                plan_id=plan.id,
                pricing_country_code=pricing_country,
                ip_country_code=ip_country,
                payment_country_code=pricing_country,
                # Dynamic unified payment columns
                payment_provider="PAYPAL",
                provider_order_id=order_id,
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
                "provider": "PAYPAL",
                "order_id": order_id,
                "amount": amount,
                "currency": currency,
                "checkout_payload": {"order_id": order_id, "links": order_data.get("links", [])},
            }

        except requests.exceptions.HTTPError as e:
            db.rollback()
            try:
                err_data = e.response.json()
                details = err_data.get("details", [])
                if details:
                    issue = details[0].get("issue")
                    description = details[0].get("description")
                    logger.error(f"PayPal Order Creation Rejected: issue={issue}, description={description}")
                    if issue == "CURRENCY_NOT_SUPPORTED":
                        raise HTTPException(
                            400,
                            f"PayPal does not support domestic transactions in '{currency.upper()}'. "
                            "Please select Razorpay instead to complete your transaction.",
                        )
                    raise HTTPException(400, f"PayPal error: {issue} - {description}")
                else:
                    message = err_data.get("message", "Unknown PayPal error")
                    logger.error(f"PayPal Order Creation Rejected: {message}")
                    raise HTTPException(400, f"PayPal error: {message}")
            except HTTPException:
                raise
            except (ValueError, AttributeError, KeyError, IndexError):
                logger.exception("PayPal order creation failed with HTTP error")
                raise HTTPException(502, f"PayPal error status: {e.response.status_code}")
        except requests.exceptions.RequestException:
            db.rollback()
            logger.exception("PayPal order creation failed due to network request error")
            raise HTTPException(502, "PayPal gateway connection failure")
        except Exception:
            db.rollback()
            logger.exception("Unexpected error during PayPal order creation")
            raise HTTPException(500, "Unable to create PayPal payment order")

    def verify_payment(self, db: Session, payload: dict, user_id: str) -> dict:
        _, _, base_url = get_paypal_config()
        token = get_paypal_access_token()

        paypal_order_id = payload.get("paypal_order_id")
        if not paypal_order_id:
            raise HTTPException(400, "Missing required PayPal order ID")

        sub = db.query(UserSubscription).filter(UserSubscription.provider_order_id == paypal_order_id).first()

        if not sub:
            raise HTTPException(404, "Subscription not found")

        if str(sub.user_id) != str(user_id):
            raise HTTPException(403, "This subscription belongs to a different user")

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

        try:
            # Execute backend-to-backend capture call
            response = requests.post(
                f"{base_url}/v2/checkout/orders/{paypal_order_id}/capture", json={}, headers=headers, timeout=15
            )

            # If already captured, we handle it gracefully or fetch the details
            if response.status_code == 422:
                # Let's inspect if order was already captured
                logger.warning(f"PayPal order {paypal_order_id} capture returned 422, fetching details")
                response = requests.get(f"{base_url}/v2/checkout/orders/{paypal_order_id}", headers=headers, timeout=10)
                response.raise_for_status()
                order_data = response.json()
            else:
                response.raise_for_status()
                order_data = response.json()

            status = order_data.get("status")
            if status != "COMPLETED":
                raise HTTPException(400, f"PayPal payment status is not completed: {status}")

            capture_id = None
            purchase_units = order_data.get("purchase_units", [])
            if purchase_units:
                payments = purchase_units[0].get("payments", {})
                captures = payments.get("captures", [])
                if captures:
                    capture_id = captures[0].get("id")

            # Update provider tracking fields
            sub.provider_payment_id = capture_id or paypal_order_id
            sub.provider_signature = "PAYPAL_VERIFIED"

            return {"subscription": sub, "payment_id": capture_id or paypal_order_id}

        except requests.exceptions.HTTPError as e:
            try:
                err_data = e.response.json()
                details = err_data.get("details", [])
                if details:
                    issue = details[0].get("issue")
                    description = details[0].get("description")
                    logger.error(f"PayPal Verification Rejected: issue={issue}, description={description}")
                    raise HTTPException(400, f"PayPal error: {issue} - {description}")
                else:
                    message = err_data.get("message", "Unknown PayPal error")
                    logger.error(f"PayPal Verification Rejected: {message}")
                    raise HTTPException(400, f"PayPal error: {message}")
            except (ValueError, AttributeError, KeyError, IndexError):
                logger.exception("PayPal verification failed with HTTP error")
                raise HTTPException(502, f"PayPal verification error status: {e.response.status_code}")
        except requests.exceptions.RequestException:
            logger.exception("PayPal payment capture/verification failed due to network request error")
            raise HTTPException(502, "PayPal gateway verification connection failure")
        except HTTPException:
            raise
        except Exception:
            logger.exception("Unexpected error during PayPal verification")
            raise HTTPException(500, "Unable to verify PayPal payment")
