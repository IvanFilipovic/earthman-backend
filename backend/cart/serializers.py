from rest_framework import serializers
from .models import CartItem, Cart

class CartItemSerializer(serializers.ModelSerializer):
    product_slug = serializers.CharField(source='product_variant.slug', read_only=True)
    product = serializers.CharField(source='product_variant.product.name', read_only=True)
    avatar_image = serializers.URLField(source='product_variant.color.avatar_image', read_only=True)
    size = serializers.CharField(source='product_variant.size', read_only=True)
    unit_price_original = serializers.DecimalField(max_digits=10, decimal_places=2, source='original_unit_price', read_only=True)
    unit_price_discounted = serializers.DecimalField(max_digits=10, decimal_places=2, source='discounted_unit_price', read_only=True)

    class Meta:
        model = CartItem
        fields = [
            'product_slug',
            'product',
            'avatar_image',
            'size',
            'quantity',
            'unit_price_original',
            'unit_price_discounted',
        ]

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    cart_total_original_price = serializers.DecimalField(max_digits=10, decimal_places=2, source='total_original_price', read_only=True)
    cart_total_discounted_price = serializers.DecimalField(max_digits=10, decimal_places=2, source='total_discounted_price', read_only=True)
    cart_total_savings = serializers.DecimalField(max_digits=10, decimal_places=2, source='total_savings', read_only=True)
    cart_total_to_pay = serializers.DecimalField(max_digits=10, decimal_places=2, source='total_to_pay', read_only=True)

    class Meta:
        model = Cart
        fields = [
            'session_id',
            'created_at',
            'updated_at',
            'items',
            'cart_total_original_price',
            'cart_total_discounted_price',
            'cart_total_savings',
            'cart_total_to_pay',
        ]