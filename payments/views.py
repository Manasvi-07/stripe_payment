from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.conf import settings
from datetime import timedelta, timezone, date
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from .models import StripePayment, Product, Price, Subscription
from accounts.models import User
from .stripe_utils import BasePayment
from django.contrib import messages
import stripe, json
from accounts.utils import send_payment_email
import logging
logger = logging.getLogger(__name__)

def home(request):
    products = Product.objects.prefetch_related("prices").all()
    return render(
        request,
        "payments/home.html",
        {
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "products": products,
        },
    )


def create_checkout_session(request):
    price_id = request.POST.get("price_id")  
    if not price_id:
        return JsonResponse({"error": "price_id is required"}, status=400)

    stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': price_id,  
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/payments/success/?session_id={CHECKOUT_SESSION_ID}'),
        cancel_url=request.build_absolute_uri('/payments/cancel/'),
    )


@csrf_exempt
def create_checkout_for_price(request, price_id):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "User not authenticated"}, status=401)

    try:
        price = Price.objects.get(stripe_price_id=price_id)
    except Price.DoesNotExist:
        return JsonResponse({"error": "Price not found"}, status=404)

    stripe_payment = BasePayment()
    is_subscription = bool(price.recurring_interval)

    session = stripe_payment.create_price_based_checkout_session(
        price_id=price.stripe_price_id,
        user=request.user,
        email=request.user.email,
        is_subscription=is_subscription,
        success_url=request.build_absolute_uri("/payments/success/"),
        cancel_url=request.build_absolute_uri("/payments/cancel/"),
        metadata={
            "user_id": str(request.user.id),
            "price_id": price.stripe_price_id,
        },
    )

    return JsonResponse({"id": session.id})

@csrf_exempt
def stripe_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method")
    
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=endpoint_secret
        )
    except ValueError:
        return HttpResponseBadRequest("Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return HttpResponseBadRequest("Invalid signature")

    logger.info(f"Webhook received: {event['type']}")

    # Handle checkout completed
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        email = session.get("customer_details", {}).get("email", "")
        metadata = session.get("metadata", {})
        amount = session.get("amount_total", 0)
        currency = session.get("currency", "usd")

        logger.info(f"Checkout completed for {email}, amount {amount}, {currency}")

        # Save payment record
        StripePayment.objects.get_or_create(
            session_id=session["id"],
            defaults={
                "email": email,
                "amount_total": amount,
                "currency": currency,
                "payment_status": session.get("payment_status", "pending")
            }
        )

        # Send email
        try:
            send_payment_email(email, amount / 100)
        except Exception as e:
            logger.error(f"Failed to send payment email: {e}")

        # Create subscription
        user = User.objects.filter(email=email).first()
        price_id = metadata.get("price_id")
        plan_id = None
        plan_name = None
        interval = "month"

        if price_id:
            try:
                price = Price.objects.get(stripe_price_id=price_id)
                interval = metadata.get("interval", "").lower() or price.recurring_interval or "month"
                product = price.product
                plan_id = product.id
                plan_name = product.name
            except Price.DoesNotExist:
                logger.warning(f"No Price found for price_id {price_id}")

        if not plan_id:
            product = Product.objects.first()
            if product:
                plan_id = product.id
                plan_name = product.name

        start_date = now()
        if interval in ["year", "yearly"]:
            end_date = start_date + timedelta(days=365)
            plan_choice = "yearly"
        else:
            end_date = start_date + timedelta(days=30)
            plan_choice = "monthly"

        if user and plan_id and plan_name:
            Subscription.objects.create(
                user_id=user.id,
                plan_id=plan_id,
                plan_name=plan_choice,
                start_date=start_date,
                end_date=end_date,
                active=True
            )
            logger.info(f"Subscription created for {email}")

    # Handle invoice payment failed
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        email = invoice.get("customer_email", "")
        logger.warning(f"Payment failed for {email}")

    # Handle subscription canceled
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription.get("customer")
        logger.info(f"Subscription canceled for customer {customer_id}")
        # You may want to deactivate Subscription in your DB

    return HttpResponse(status=200)

def success(request):
    session_id = request.GET.get("session_id")
    if session_id:
        stripe.checkout.Session.retrieve(session_id)
    messages.success(request, "Payment completed successfully!")
    return render(request, "payments/success.html")

def cancel(request):
    return render(request, "payments/cancel.html")


def create_stripe_product_and_price(name, description, amount_cents, interval="month", currency="usd"):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe_product = stripe.Product.create(name=name, description=description)
    price_data = {
        "product": stripe_product.id,
        "unit_amount": amount_cents,
        "currency": currency,
    }

    if interval:
        price_data["recurring"] = {"interval": interval}

    stripe_price = stripe.Price.create(**price_data)

    product = Product.objects.create(
        name=name, description=description, stripe_product_id=stripe_product.id
    )

    Price.objects.create(
        product=product,
        stripe_price_id=stripe_price.id,
        unit_amount=amount_cents,
        currency=currency,
        recurring_interval=interval or "",
    )

    return product