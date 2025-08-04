from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create-checkout-session/', views.create_checkout_session, name='checkout'),
    path('create-checkout/<int:price_id>/', views.create_checkout_for_price, name='create_checkout_price'),
    path('webhook/', views.stripe_webhook, name='webhook'),
    path('success/', views.success, name='success'),
    path('cancel/', views.cancel, name='cancel'),
]