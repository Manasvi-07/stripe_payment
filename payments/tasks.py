from celery import shared_task  
from django.utils.timezone import now
from datetime import timedelta
from .models import Subscription    
from accounts.utils import send_custom_email
from django.conf import settings


@shared_task
def send_subscription_reminders():
    expiring_subs = Subscription.objects.filter(
        end_date__lte=now() + timedelta(days=5),
        end_date__gt=now(),
        active=True
    )

    for sub in expiring_subs:
        send_custom_email(
            to_email=sub.user.email,
            subject=sub.plan_name,
            message=sub.end_date.strftime("%Y-%m-%d"),
            from_email=settings.DEFAULT_FROM_EMAIL,
            plan_name=sub.plan_name
        )