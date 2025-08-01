from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from .models import StripePayment, Product, Price
from .stripe_utils import BasePayment
import stripe, json

def home(request):
    return render(request, 'payments/home.html', {
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'products': Product.objects.prefetch_related('prices')
    })

def create_checkout_session(request):
    stripe_payment = BasePayment()
    email = request.GET.get('email')
    session = stripe_payment.create_checkout_session('Test Product', 2000, email)
    return JsonResponse({'id': session.id})

@csrf_exempt
def create_checkout_for_price(request, price_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    try:
        price = Price.objects.get(id=price_id)
    except Price.DoesNotExist:
        return JsonResponse({'error': 'Price not found'}, status=404)

    stripe_payment = BasePayment()
    session = stripe_payment.create_price_based_checkout_session(price.stripe_price_id, email)
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
            StripePayment.objects.create(
                session_id=session['id'],
                email=session.get("customer_email") or session.get("customer_details", {}).get("email", ""),
                amount_total=session.get('amount_total', 0) / 100,
                currency=session.get('currency', 'usd'),
                payment_status=session.get('payment_status', ''),
            )

    except Exception as e:
        print(" ERROR processing webhook:", e)
        return HttpResponse(status=500)

    return HttpResponse(status=200)

def success(request):
    request.session["cart"] = []
    return render(request, 'payments/success.html')

def cancel(request):
    return render(request, 'payments/cancel.html')

def create_stripe_product_and_price(name, description, amount_cents, currency='usd'):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe_product = stripe.Product.create(name=name, description=description)
    stripe_price = stripe.Price.create(
        product=stripe_product.id,
        unit_amount=amount_cents,
        currency=currency,
    )

    product = Product.objects.create(
        name=name,
        description=description,
        stripe_product_id=stripe_product.id
    )

    Price.objects.create(
        product=product,
        stripe_price_id=stripe_price.id,
        unit_amount=amount_cents,
        currency=currency
    )

    return product

@csrf_exempt
def add_to_cart(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        product = Product.objects.get(id=product_id)
        price = product.prices.first()
        email = request.POST.get("email")

        request.session["user_email"] = email
        cart = request.session.get("cart", [])

        for item in cart:
            if isinstance(item, dict) and item.get("product_id") == product.id:
                return JsonResponse({"message": "Already in cart"}, status=200)

        cart.append({
            "product_id": product.id,
            "price_id": price.stripe_price_id,
        })

        request.session["cart"] = cart
        return JsonResponse({"message": "Added to cart"}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt
def checkout_cart(request):
    if request.method == "POST":
        cart = request.session.get("cart", [])
        email = request.session.get("user_email")
        price_ids = []
        for item in cart:
            if isinstance(item, dict):
                price_ids.append(item.get("price_id"))

        if not cart:
            return JsonResponse({'error': 'Cart is empty.'}, status=400)
        
        price_ids = [item['price_id'] for item in cart]
        prices = Price.objects.filter(stripe_price_id__in=price_ids)
        
        if not prices.exists():
            return JsonResponse({'error': 'No valid prices found.'}, status=400)

        stripe_payment = BasePayment()
        email = request.user.email if request.user.is_authenticated else None
        session = stripe_payment.create_checkout_session_for_cart(prices, email)

        return redirect(session.url, code=303)

    return JsonResponse({'error': 'Invalid request method.'}, status=400)

def cart_view(request):
    cart = request.session.get("cart", [])
    products = []
    total = 0

    for item in cart:
        try:
            price = get_object_or_404(Price, stripe_price_id=item["price_id"])
            product = Product.objects.get(id=item["product_id"])
            products.append({
                "product": product,
                "price": price,
                "unit_amount": price.unit_amount,
                "price_id": item["price_id"]
            })
            total += price.unit_amount
        except Product.DoesNotExist:
            continue

    return render(request, "payments/cart.html", {"products": products, "total": total/100})

def clear_cart(request):
    if "cart" in request.session:
        del request.session["cart"]
    return JsonResponse({"message": "Cart cleared."})