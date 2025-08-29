import stripe
from django.conf import settings
from django.http import JsonResponse

class BasePayment:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_checkout_session(self, request):
        price_id = request.GET.get("price_id")

        session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='subscription',
        line_items=[{
            'price': price_id,
            'quantity': 1,
        }],
        success_url="http://localhost:8000/payments/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="http://localhost:8000/payments/cancel/",
    )

        return JsonResponse({"id": session.id})

    def create_price_based_checkout_session(self, price_id, user=None, email=None, is_subscription=False, success_url=None, cancel_url=None, metadata=None):
        if not (user or email):
            raise ValueError("Email is required for Stripe checkout session.")

        session_data = {
            "payment_method_types": ["card"],
            "line_items": [{"price": price_id, "quantity": 1}],
            "mode": "subscription" if is_subscription else "payment",
            "success_url": success_url or "http://localhost:8000/payments/success/",
            "cancel_url": cancel_url or "http://localhost:8000/payments/cancel/",
            "customer_email": user.email,
            "metadata": metadata or {
                "user_id": user.id,
                "price_id": price_id,
            },
        }

        if email or getattr(user, "email", None):
            session_data["customer_email"] = email or getattr(user, "email", None)

        return stripe.checkout.Session.create(**session_data)

    def verify_webhook_signature(self, payload, sig_header):
        try:
            return stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except Exception:
            return None
        

