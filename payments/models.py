from django.db import models
from django.conf import settings
from datetime import timedelta
from django.utils import timezone

class StripePayment(models.Model):
    session_id = models.CharField(max_length=255)
    email = models.EmailField()
    amount_total = models.IntegerField()
    currency = models.CharField(max_length=10)
    payment_status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} - {self.amount_total} {self.currency}"

class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    stripe_product_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

class Price(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices')
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)
    currency = models.CharField(max_length=10, default='usd')
    unit_amount = models.IntegerField(help_text="Amount in cents")
    recurring_interval = models.CharField(max_length=10, choices=[('month', 'Monthly'), ('year', 'Yearly'), ('weekly', 'Weekly'),('', 'One-time')], default='')

    def __str__(self):
        suffix = f" - {self.recurring_interval}" if self.recurring_interval else ""
        return f"{self.unit_amount / 100:.2f} {self.currency.upper()} - {self.product.name}{suffix}"

class Subscription(models.Model):
    PLAN_CHOICES = [
        ('weekly', '1 Week'),
        ('monthly', '1 Month'),
        ('yearly', '1 Year'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey('payments.Product', null=True, blank=True, on_delete=models.SET_NULL)
    plan_name = models.CharField(max_length=20, choices=PLAN_CHOICES, blank=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.end_date:
            if self.plan_name == 'monthly':
                self.end_date = timezone.now() + timedelta(days=30)
            elif self.plan_name == 'yearly':
                self.end_date = timezone.now() + timedelta(days=365)
            elif self.plan_name == 'weekly':
                self.end_date = timezone.now() + timedelta(days=7)    
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.plan_name or (self.plan.name if self.plan else 'plan')}"