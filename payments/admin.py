from django.contrib import admin
from .models import StripePayment, Product, Price

class StripePaymentAdmin(admin.ModelAdmin):
     list_display = ('session_id', 'email', 'amount_total', 'currency', 'payment_status', 'created_at')

admin.site.register(StripePayment, StripePaymentAdmin)
admin.site.register(Product)
admin.site.register(Price)