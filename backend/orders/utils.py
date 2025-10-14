# utils.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

def build_order_confirmation_email(order):
    subject = f"Order Confirmation - {order.order_reference}"
    message = render_to_string("emails/order_confirmation.txt", {"order": order})
    return subject, message

def build_order_shipped_email(order):
    subject = f"Your Order {order.order_reference} Has Been Shipped!"
    message = render_to_string("emails/order_shipped.txt", {"order": order})
    return subject, message
