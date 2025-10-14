from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_reference', 'user', 'guest', 'payment_method', 'payment_status', 'created_at')
    search_fields = ('order_reference',)
    inlines = [OrderItemInline]