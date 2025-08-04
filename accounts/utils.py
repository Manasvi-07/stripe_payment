from django.core.mail import send_mail
from django.conf import settings

def send_payment_email(to_email, amount):
    if to_email:
        subject = 'Payment Confirmation'
        message = f'Thank you! Your payment of ${amount} was successful.'
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(subject, message, from_email, [to_email])