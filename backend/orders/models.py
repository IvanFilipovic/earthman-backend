from django.conf import settings
from django.db import models
from common.models import ProductVariant
from customers.models import Guest
import uuid
from decimal import Decimal

def generate_order_reference():
    return f"ORD-{uuid.uuid4().hex[:10].upper()}"

# ------------------
# 🧾 Updated Order Models (for IPG)
# ------------------

class Order(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
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
    country = models.CharField(max_length=72,blank=True)
    address = models.CharField(max_length=72)
    city = models.CharField(max_length=48)
    postal_code = models.CharField(max_length=10)
    delivery_address = models.CharField(max_length=72,blank=True)
    delivery_city = models.CharField(max_length=48,blank=True)
    delivery_postal_code = models.CharField(max_length=10,blank=True)
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
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, choices=ORDER_STATUS, default="processing")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._previous_status = self.status  # Store current value

    def save(self, *args, **kwargs):
        if self.pk:  # instance already exists
            old = Order.objects.get(pk=self.pk)
            self._previous_status = old.status
        super().save(*args, **kwargs)

    def get_recipient_email(self):
        if self.user:
            return self.user.email
        elif self.guest:
            return self.guest.email
        return self.email


    def calculate_total(self):
        total = Decimal('0.00')  # Ensure we start with a Decimal value.
        for item in self.items.select_related('product_variant__product'):
            product = item.product_variant.product
            # Ensure both product price and discount price are Decimals
            unit_price = Decimal(str(product.discount_price if product.discount and product.discount_price else product.price))
            total += unit_price * item.quantity

        # Ensure shipping cost is a Decimal as well
        total += Decimal(str(self.shipping_cost))  # Convert shipping cost to Decimal
        return total
    
    def __str__(self):
        return f"Order {self.order_reference} by {self.email}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product_variant} for Order {self.order_id}"