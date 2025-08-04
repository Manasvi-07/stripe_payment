import stripe
from django.conf import settings

class BasePayment:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_checkout_session(self, product_name, amount, currency='usd', email=None, is_subscription=False):
        session_data = {
            "payment_method_types": ['card'],
            "line_items": [{
                "price_data": {
                    "currency": currency,
                    "unit_amount": amount,
                    "product_data": {"name": product_name},
                    "recurring": {"interval": "month"} if is_subscription else None
                },
                "quantity": 1,
            }],
            "mode": "subscription" if is_subscription else "payment",
            "customer_email": email,
            "success_url": "http://localhost:8000/success/",
            "cancel_url": "http://localhost:8000/cancel/"
        }
        return stripe.checkout.Session.create(**session_data)

    def create_price_based_checkout_session(self, price_id, email=None, is_subscription=False):
        return stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{"price": price_id, "quantity": 1}],
        mode='subscription' if is_subscription else 'payment',
        customer_email=email,
        success_url='http://localhost:8000/success/',
        cancel_url='http://localhost:8000/cancel/',
    )

    def verify_webhook_signature(self, payload, sig_header):
        try:
            return stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except Exception:
            return None
        

