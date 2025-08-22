from django.urls import path
from .views import HomeView, CreateCheckoutSessionView, CreateCheckoutForPriceView, StripeWebhookView, SuccessView, CancelView
urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('create-checkout-session/', CreateCheckoutSessionView.as_view(), name='checkout'),
    path('create-checkout/<str:price_id>/', CreateCheckoutForPriceView.as_view(), name='create_checkout_price'),
    path('stripe/webhook/', StripeWebhookView.as_view(), name='webhook'),
    path('success/', SuccessView.as_view(), name='success'),
    path('cancel/', CancelView.as_view(), name='cancel'),
]