from celery import shared_task
from django.core.mail import send_mail, EmailMultiAlternatives, get_connection
from django.conf import settings
from orders.models import Order
from orders.utils import build_order_confirmation_email, build_order_shipped_email

@shared_task
def send_order_confirmation_email_task(order_id):
    try:
        order = Order.objects.get(id=order_id)
        email = order.get_recipient_email()
        if not email:
            return
        
        subject, message = build_order_confirmation_email(order)
        def send_email_with_connection(subject, message, recipient, html_message=None):
            connection = get_connection(fail_silently=False)
            email = EmailMultiAlternatives(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                connection=connection
            )
            if html_message:
                email.attach_alternative(html_message, "text/html")
            email.send()
        send_email_with_connection(subject, message, email)
    except Order.DoesNotExist:
        pass

@shared_task
def send_order_shipped_email_task(order_id):
    try:
        order = Order.objects.get(id=order_id)
        email = order.get_recipient_email()
        if not email:
            return
        
        subject, message = build_order_shipped_email(order)
        def send_email_with_connection(subject, message, recipient, html_message=None):
            connection = get_connection(fail_silently=False)
            email = EmailMultiAlternatives(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                connection=connection
            )
            if html_message:
                email.attach_alternative(html_message, "text/html")
            email.send()
        send_email_with_connection(subject, message, email)
    except Order.DoesNotExist:
        pass
