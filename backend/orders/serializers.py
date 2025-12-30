# orders/serializers.py
from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    product_variant_slug = serializers.CharField(source='product_variant.slug', read_only=True)
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['product_variant_slug', 'product_name', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'order_reference',
            'payment_method',
            'payment_status',
            'total_price',
            'shipping_cost',
            'created_at',
            'items',
            'stripe_client_secret',
            'paypal_order_id',
        ]
        read_only_fields = ['stripe_client_secret', 'paypal_order_id']