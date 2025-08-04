from django.db import models

class StripePayment(models.Model):
    session_id = models.CharField(max_length=255)
    email = models.EmailField()
    amount_total = models.IntegerField()
    currency = models.CharField(max_length=10)
    payment_status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} - {self.amount_total / 100:.2f} {self.currency.upper()} - {self.payment_status}"

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
    recurring_interval = models.CharField(max_length=10, choices=[('month', 'Monthly'), ('year', 'Yearly'), ('', 'One-time')], default='')

    def __str__(self):
        suffix = f" - {self.recurring_interval}" if self.recurring_interval else ""
        return f"{self.unit_amount / 100:.2f} {self.currency.upper()} - {self.product.name}{suffix}"
