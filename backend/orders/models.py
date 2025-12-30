# orders/models.py

from django.conf import settings
from django.db import models
from common.models import ProductVariant
from customers.models import Guest
import uuid
from decimal import Decimal

def generate_order_reference():
    return f"ORD-{uuid.uuid4().hex[:10].upper()}"


class Order(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    ORDER_STATUS = [
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('cashOnDelivery', 'Cash on delivery'),
        ('card', 'Card'),
        ('bankTransfer', 'Bank transfer'),
        ('paypal', 'PayPal'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='orders'
    )
    guest = models.ForeignKey(
        Guest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    email = models.EmailField(blank=True, null=True)
    country = models.CharField(max_length=72, blank=True)
    address = models.CharField(max_length=72)
    city = models.CharField(max_length=48)
    postal_code = models.CharField(max_length=10)
    delivery_address = models.CharField(max_length=72, blank=True)
    delivery_city = models.CharField(max_length=48, blank=True)
    delivery_postal_code = models.CharField(max_length=10, blank=True)
    phone_number = models.CharField(max_length=15)
    
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    order_reference = models.CharField(
        blank=False,
        max_length=100, 
        unique=True, 
        default=generate_order_reference
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=10.00)
    created_at = models.DateTimeField(auto_now_add=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_client_secret = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default="processing")
    paypal_order_id = models.CharField(max_length=255, blank=True, null=True)
    paypal_payer_id = models.CharField(max_length=255, blank=True, null=True)
    tracking_number = models.CharField(max_length=255, blank=True, null=True)
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    # ✅ New field to track if shipping email was sent
    shipping_email_sent = models.BooleanField(default=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._previous_status = self.status  # Store current status

    def save(self, *args, **kwargs):
        # Check if this is an existing order (has pk)
        if self.pk:
            old = Order.objects.get(pk=self.pk)
            self._previous_status = old.status
            
            # ✅ Check if status changed to 'shipped'
            status_changed_to_shipped = (
                self._previous_status != 'shipped' and 
                self.status == 'shipped'
            )
            
            # Save the order first
            super().save(*args, **kwargs)
            
            # Send shipping email if status changed to shipped
            if status_changed_to_shipped and not self.shipping_email_sent:
                # Import here to avoid circular imports
                from .emails import send_shipping_confirmation
                
                if send_shipping_confirmation(self):
                    self.shipping_email_sent = True
                    # Use update to avoid recursion
                    Order.objects.filter(pk=self.pk).update(shipping_email_sent=True)
        else:
            # New order, just save
            super().save(*args, **kwargs)

    def get_recipient_email(self):
        if self.user:
            return self.user.email
        elif self.guest:
            return self.guest.email
        return self.email

    @property
    def subtotal(self):
        """Calculate subtotal (total - shipping)"""
        if self.total_price and self.shipping_cost:
            return self.total_price - self.shipping_cost
        return self.total_price or Decimal('0.00')
    
    def get_item_price(self, item):
        """Get unit price for an order item"""
        product = item.product_variant.product
        if product.discount and product.discount_price:
            return Decimal(str(product.discount_price))
        return Decimal(str(product.price))
    
    def get_item_total(self, item):
        """Get total price for an order item"""
        return self.get_item_price(item) * item.quantity

    def calculate_total(self):
        total = Decimal('0.00')
        for item in self.items.select_related('product_variant__product'):
            product = item.product_variant.product
            unit_price = Decimal(str(product.discount_price if product.discount and product.discount_price else product.price))
            total += unit_price * item.quantity
        total += Decimal(str(self.shipping_cost))
        return total
    
    def __str__(self):
        return f"Order {self.order_reference} by {self.email}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product_variant} for Order {self.order_id}"