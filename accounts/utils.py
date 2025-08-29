from django.core.mail import send_mail
from django.conf import settings

def send_payment_email(to_email, amount):
    if to_email:
        subject = 'Payment Confirmation'
        message = f'Thank you! Your payment of ${amount} was successful.'
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(subject, message, from_email, [to_email])

def send_custom_email(to_email, plan, plan_name, subject, message, from_email=None):
    if to_email:
        subject = "Your subscription is expiring soon!"
        message = (
            f"Hi {to_email}"
            f"will expire on {message}. "
            f"your {plan}, {plan_name}."
            "Please renew before it ends."
        )
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(subject, message, plan, plan_name, from_email, [to_email])