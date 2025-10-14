from django.db import models
from common.models import ProductVariant

# ------------------
# 🛒 Cart Models
# ------------------

class Cart(models.Model):
    session_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart {self.session_id}"

    @property
    def total_original_price(self):
        return sum(item.original_total for item in self.items.all())

    @property
    def total_discounted_price(self):
        return sum(item.discounted_total for item in self.items.all())

    @property
    def total_savings(self):
        return self.total_original_price - self.total_discounted_price

    @property
    def total_to_pay(self):
        return self.total_discounted_price

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product_variant')

    def __str__(self):
        return f"{self.quantity} x {self.product_variant} in cart {self.cart_id}"

    @property
    def original_unit_price(self):
        return self.product_variant.product.price

    @property
    def discounted_unit_price(self):
        product = self.product_variant.product
        if product.discount and product.discount_price:
            return product.discount_price
        return product.price  # important: fallback to full price

    @property
    def original_total(self):
        return self.original_unit_price * self.quantity

    @property
    def discounted_total(self):
        return self.discounted_unit_price * self.quantity

    @property
    def total_savings(self):
        return self.original_total - self.discounted_total