from django.core.management.base import BaseCommand
import stripe
from payments.models import Product, Price
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

class Command(BaseCommand):
    help = "Sync products and prices from Stripe into the local DB"

    def handle(self, *args, **kwargs):
        products = stripe.Product.list(limit=100)
        for p in products.auto_paging_iter():
            product, _ = Product.objects.update_or_create(
                stripe_product_id=p.id,
                defaults={
                    "name": p.name,
                    "description": p.description or ""
                }
            )
            self.stdout.write(self.style.SUCCESS(f"Synced product: {product.name}"))

            prices = stripe.Price.list(product=p.id, limit=100)
            for pr in prices.auto_paging_iter():
                price, _ = Price.objects.update_or_create(
                    stripe_price_id=pr.id,
                    product=product,
                    defaults={
                        "currency": pr.currency,
                        "unit_amount": pr.unit_amount,
                        "recurring_interval": pr.recurring["interval"] if pr.type == "recurring" else ""
                    }
                )
                self.stdout.write(self.style.SUCCESS(f"  -> Synced price: {price.unit_amount/100:.2f} {price.currency}/{price.recurring_interval or 'one-time'}"))
