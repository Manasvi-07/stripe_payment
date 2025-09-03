from django.core.mail import send_mail
from django.conf import settings

def send_payment_email(to_email, amount):
    if to_email:
        subject = 'Payment Confirmation'
        message = f'Thank you! Your payment of ${amount} was successful.'
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(subject, message, from_email, [to_email])

def send_custom_email(to_email, plan_name, end_date, from_email=None):
    if to_email:
        subject = "Your subscription is expiring soon!"
        message = (
            f"Hi {to_email},\n\n"
            f"Your subscription for {plan_name} will expire on {end_date}.\n"
            "Please renew before it ends."
        )
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(subject, message, from_email, [to_email])