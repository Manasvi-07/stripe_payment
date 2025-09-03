from django.conf import settings
import logging
import os

logger = logging.getLogger('payments')

def handle_checkout_completed(session):
    customer_email = session.get("customer_details", {}).get("email")
    subscription_id = session.get("subscription")
    payment_intent_id = session.get("payment_intent")

    logger.info(
        "Checkout completed | Email=%s | Subscription=%s | PaymentIntent=%s | Amount=%s %s",
        customer_email,
        subscription_id,
        payment_intent_id,
        session.get("amount_total"),
        session.get("currency"),
    )

def handle_payment_failed(invoice):
    customer_email = invoice.get("customer_email")
    subscription_id = invoice.get("subscription")

    logger.warning(
        "Payment failed | Email=%s | Subscription=%s | Amount Due=%s %s",
        customer_email,
        subscription_id,
        invoice.get("amount_due"),
        invoice.get("currency"),
    )
