from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from .models import StripePayment, Product, Price
from .stripe_utils import BasePayment
from django.contrib import messages
import stripe, json
from accounts.utils import send_payment_email

def home(request):
    products = Product.objects.prefetch_related('prices').all()
    return render(request, 'payments/home.html', {
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'products': products
    })

def create_checkout_session(request):
    stripe_payment = BasePayment()
    email = request.user.email if request.user.is_authenticated else request.GET.get('email')
    session = stripe_payment.create_checkout_session('Test Product', 2000, email)
    return JsonResponse({'id': session.id})

@csrf_exempt
@csrf_exempt
def create_checkout_for_price(request, price_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    try:
        email = request.user.email
    except Exception:
        return JsonResponse({'error': 'User email not available'}, status=400)

    try:
        price = Price.objects.get(id=price_id)
    except Price.DoesNotExist:
        return JsonResponse({'error': 'Price not found'}, status=404)

    stripe_payment = BasePayment()
    is_subscription = bool(price.recurring_interval)
    session = stripe_payment.create_price_based_checkout_session(
        price.stripe_price_id,
        email=email,
        is_subscription=is_subscription
    )
    return JsonResponse({'id': session.id})


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        print("Invalid payload:", e)
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        print("Invalid signature:", e)
        return HttpResponse(status=400)

    try:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            email = session.get("customer_email") or session.get("customer_details", {}).get("email", "")
            amount = session.get('amount_total', 0) / 100

            StripePayment.objects.create(
                session_id=session['id'],
                email=email,
                amount_total=amount,
                currency=session.get('currency', 'usd'),
                payment_status=session.get('payment_status', ''),
            )

            send_payment_email(email, amount)

    except Exception as e:
        print(" ERROR processing webhook:", e)
        return HttpResponse(status=500)

    return HttpResponse(status=200)

def success(request):
    request.session["cart"] = []
    messages.success(request, "Payment completed successfully!")
    return render(request, 'payments/success.html')

def cancel(request):
    return render(request, 'payments/cancel.html')

def create_stripe_product_and_price(name, description, amount_cents, interval='month', currency='usd'):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe_product = stripe.Product.create(name=name, description=description)
    price_data = {
        'product': stripe_product.id,
        'unit_amount': amount_cents,
        'currency': currency
    }

    if interval:
        price_data['recurring'] = {"interval": interval}

    stripe_price = stripe.Price.create(**price_data)

    product = Product.objects.create(
        name=name,
        description=description,
        stripe_product_id=stripe_product.id
    )

    Price.objects.create(
        product=product,
        stripe_price_id=stripe_price.id,
        unit_amount=amount_cents,
        currency=currency,
        recurring_interval=interval or ''
    )

    return product

