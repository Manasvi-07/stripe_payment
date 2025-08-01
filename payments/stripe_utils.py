import stripe
from django.conf import settings

class BasePayment:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_checkout_session(self, product_name, amount, currency='usd', email=None):
        return stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'unit_amount': amount,
                    'product_data': {'name': product_name},
                },
                'quantity': 1,
            }],
            mode='payment',
            customer_email=email,
            success_url='http://localhost:8000/success/',
            cancel_url='http://localhost:8000/cancel/',
        )

    def create_price_based_checkout_session(self, price_id, email=None):
        return stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='payment',
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
        
    def create_checkout_session_for_cart(self, prices, email=None):
        line_items = [
            {
                'price': price.stripe_price_id,
                'quantity': 1,
            }
            for price in prices
        ]
    
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer_email=email,
            success_url='http://localhost:8000/success/',
            cancel_url='http://localhost:8000/cancel/',
            
        )
        return session
