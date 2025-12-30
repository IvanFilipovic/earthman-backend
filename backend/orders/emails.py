# orders/emails.py

from django.utils import timezone
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)


def send_order_emails(order):
    """
    Send order confirmation emails to both customer and staff
    Only sends once - prevents duplicates
    
    Args:
        order: Order instance
        
    Returns:
        tuple: (customer_success, staff_success)
    """
    # Check if emails already sent
    if order.email_sent:
        logger.info(f"⏭️  Emails already sent for order {order.order_reference}, skipping")
        return (True, True)
    
    # Send emails
    customer_success = send_customer_confirmation(order)
    staff_success = send_staff_notification(order)
    
    # Mark as sent if both succeeded
    if customer_success and staff_success:
        order.email_sent = True
        order.email_sent_at = timezone.now()
        order.save(update_fields=['email_sent', 'email_sent_at'])
        logger.info(f"✅ Emails sent and marked for order {order.order_reference}")
    
    return (customer_success, staff_success)


def send_customer_confirmation(order):
    """Send order confirmation email to customer"""
    try:
        context = {
            'order': order,
            'frontend_url': settings.FRONTEND_URL,
            'current_year': timezone.now().year,
        }
        
        html_content = render_to_string('emails/customer_order_confirmation.html', context)
        text_content = render_to_string('emails/customer_order_confirmation.txt', context)
        
        subject = f'Order Confirmation - {order.order_reference}'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [order.email]
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=to_email
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"✅ Customer email sent to {order.email} for order {order.order_reference}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send customer email for {order.order_reference}: {str(e)}")
        return False


def send_staff_notification(order):
    """Send order notification email to staff"""
    try:
        context = {
            'order': order,
            'frontend_url': settings.FRONTEND_URL,
            'current_year': timezone.now().year,
        }
        
        html_content = render_to_string('emails/staff_order_notification.html', context)
        text_content = render_to_string('emails/staff_order_notification.txt', context)
        
        subject = f'🔔 New Order {order.order_reference} - €{order.total_price}'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [settings.STAFF_ORDER_EMAIL]
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=to_email
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"✅ Staff notification sent to {settings.STAFF_ORDER_EMAIL} for order {order.order_reference}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send staff notification for {order.order_reference}: {str(e)}")
        return False


def send_payment_failed_emails(order):
    """Send payment failed notifications to customer and staff"""
    # Only send if not already in failed state
    customer_success = False
    staff_success = False
    
    try:
        # Customer notification
        subject_customer = f'Payment Issue - Order {order.order_reference}'
        message_customer = f"""
Dear Customer,

We encountered an issue processing your payment for order {order.order_reference}.

Order Details:
- Order Number: {order.order_reference}
- Total Amount: €{order.total_price}

Please contact our support team at orders@earth-man.eu or try placing your order again.

Best regards,
The EARTHMAN Team
        """
        
        email_customer = EmailMultiAlternatives(
            subject=subject_customer,
            body=message_customer,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.email]
        )
        email_customer.send(fail_silently=False)
        customer_success = True
        logger.info(f"✅ Payment failed email sent to customer {order.email}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send payment failed email to customer: {str(e)}")
    
    try:
        # Staff notification
        subject_staff = f'⚠️ Payment Failed - Order {order.order_reference}'
        message_staff = f"""
PAYMENT FAILED ALERT

Order: {order.order_reference}
Customer: {order.email}
Amount: €{order.total_price}
Payment Method: {order.payment_method}

Transaction ID: {order.transaction_id or 'N/A'}

Action: Follow up with customer.
        """
        
        email_staff = EmailMultiAlternatives(
            subject=subject_staff,
            body=message_staff,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.STAFF_ORDER_EMAIL]
        )
        email_staff.send(fail_silently=False)
        staff_success = True
        logger.info(f"✅ Payment failed notification sent to staff")
        
    except Exception as e:
        logger.error(f"❌ Failed to send payment failed notification to staff: {str(e)}")
    
    return (customer_success, staff_success)


def send_shipping_confirmation(order):
    """
    Send shipping confirmation email to customer with tracking number
    
    Args:
        order: Order instance with status='shipped' and tracking_number set
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Check if tracking number exists
        if not order.tracking_number:
            logger.warning(f"⚠️ No tracking number for order {order.order_reference}, email not sent")
            return False
        
        context = {
            'order': order,
            'frontend_url': settings.FRONTEND_URL,
            'current_year': timezone.now().year,
        }
        
        html_content = render_to_string('emails/shipping_confirmation.html', context)
        text_content = render_to_string('emails/shipping_confirmation.txt', context)
        
        subject = f'Your Order Has Shipped - {order.order_reference}'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [order.email]
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=to_email
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"✅ Shipping confirmation sent to {order.email} for order {order.order_reference} (Tracking: {order.tracking_number})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send shipping confirmation for {order.order_reference}: {str(e)}")
        return False
