from django.views import View
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.contrib import messages
from django.utils.timezone import now
from datetime import timedelta
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import StripePayment, Product, Price, Subscription
from accounts.models import User
from .stripe_utils import BasePayment
from accounts.utils import send_payment_email

import stripe, logging

logger = logging.getLogger(__name__)


# Home page
class HomeView(TemplateView):
    template_name = "payments/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stripe_publishable_key"] = settings.STRIPE_PUBLISHABLE_KEY
        context["products"] = Product.objects.prefetch_related("prices").all()
        return context


# Simple Checkout session creation
class CreateCheckoutSessionView(View):
    def post(self, request, *args, **kwargs):
        price_id = request.POST.get("price_id")
        if not price_id:
            return JsonResponse({"error": "price_id is required"}, status=400)

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{"price": price_id, "quantity": 1}],
            mode='payment',
            success_url=request.build_absolute_uri(
                '/payments/success/?session_id={CHECKOUT_SESSION_ID}'
            ),
            cancel_url=request.build_absolute_uri('/payments/cancel/'),
        )
        return JsonResponse({"id": session.id})


# Checkout for a specific price
@method_decorator(csrf_exempt, name="dispatch")
class CreateCheckoutForPriceView(View):
    def post(self, request, price_id, *args, **kwargs):
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


# Stripe Webhook
@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        endpoint_secret = settings.STRIPE_WEBHOOK_KEY

        try:
            event = stripe.Webhook.construct_event(
                payload=payload, sig_header=sig_header, secret=endpoint_secret
            )
        except ValueError:
            return HttpResponseBadRequest("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return HttpResponseBadRequest("Invalid signature")

        logger.info(f"Webhook received: {event['type']}")

        if event['type'] == 'checkout.session.completed':
            self.handle_checkout_completed(event)
        elif event['type'] == 'invoice.payment_failed':
            self.handle_payment_failed(event)
        elif event['type'] == 'customer.subscription.deleted':
            self.handle_subscription_canceled(event)

        return HttpResponse(status=200)

    def handle_checkout_completed(self, event):
        session = event['data']['object']
        email = session.get("customer_details", {}).get("email", "")
        metadata = session.get("metadata", {})
        amount = session.get("amount_total", 0)
        currency = session.get("currency", "usd")

        logger.info(f"Checkout completed for {email}, amount {amount}, {currency}")

        StripePayment.objects.get_or_create(
            session_id=session["id"],
            defaults={
                "email": email,
                "amount_total": amount,
                "currency": currency,
                "payment_status": session.get("payment_status", "pending"),
            },
        )

        try:
            send_payment_email(email, amount / 100)
        except Exception as e:
            logger.error(f"Failed to send payment email: {e}")

        user = User.objects.filter(email=email).first()
        price_id = metadata.get("price_id")
        plan_id, plan_name, interval = None, None, "month"

        if price_id:
            try:
                price = Price.objects.get(stripe_price_id=price_id)
                interval = (
                    metadata.get("interval", "").lower()
                    or price.recurring_interval
                    or "month"
                )
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
        elif interval in ["week", "weekly"]:
            end_date = start_date + timedelta(days=7)
            plan_choice = "weekly"
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
                active=True,
            )
            logger.info(f"Subscription created for {email}")

    def handle_payment_failed(self, event):
        invoice = event['data']['object']
        email = invoice.get("customer_email", "")
        logger.warning(f"Payment failed for {email}")

    def handle_subscription_canceled(self, event):
        subscription = event['data']['object']
        customer_id = subscription.get("customer")
        logger.info(f"Subscription canceled for customer {customer_id}")


# Success and Cancel 
class SuccessView(TemplateView):
    template_name = "payments/success.html"

    def get(self, request, *args, **kwargs):
        session_id = request.GET.get("session_id")
        if session_id:
            stripe.checkout.Session.retrieve(session_id)
        messages.success(request, "Payment completed successfully!")
        return render(request, self.template_name)


class CancelView(TemplateView):
    template_name = "payments/cancel.html"


class CreateStripeProductAndPrice:
    @staticmethod
    def create(name, description, amount_cents, interval="month", currency="usd"):
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
