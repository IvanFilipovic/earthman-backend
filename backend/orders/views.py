from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.conf import settings

from .models import Order, OrderItem
from .serializers import OrderSerializer
from cart.models import Cart
from customers.models import Guest

class CreateOrderView(APIView):
    def post(self, request):
        session_id = request.COOKIES.get(settings.CART_SESSION_COOKIE)
        if not session_id:
            return Response({"detail": "Session not found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.prefetch_related('items__product_variant__product').get(session_id=session_id)
            if not cart.items.exists():
                return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)
        except Cart.DoesNotExist:
            return Response({"detail": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)

        # Extract user info
        customer_data = {
            "email": request.data.get("email"),
            "country": request.data.get("country"),
            "delivery_address": request.data.get("delivery_address"),
            "delivery_city": request.data.get("delivery_city"),
            "delivery_postal_code": request.data.get("delivery_postal_code"),
            "address": request.data.get("address"),
            "city": request.data.get("city"),
            "postal_code": request.data.get("postal_code"),
            "phone_number": request.data.get("phone_number"),
            "payment_method": request.data.get("payment_method"),
            "shipping_cost": request.data.get("shipping_cost"),
        }

        if not all(customer_data.values()):
            return Response({"detail": "Missing customer fields."}, status=status.HTTP_400_BAD_REQUEST)

        user = None
        guest = None

        # Check if user is authenticated
        if request.user.is_authenticated:
            user = request.user
        else:
            # Handle guest
            guest, created = Guest.objects.get_or_create(email=customer_data["email"])

        # Create order
        order = Order.objects.create(
            user=user,
            guest=guest,
            email=customer_data["email"],
            country=customer_data["country"],
            address=customer_data["address"],
            city=customer_data["city"],
            postal_code=customer_data["postal_code"],
            delivery_address=customer_data["delivery_address"],
            delivery_city=customer_data["delivery_city"],
            delivery_postal_code=customer_data["delivery_postal_code"],
            phone_number=customer_data["phone_number"],
            payment_method=customer_data["payment_method"],
            shipping_cost=customer_data["shipping_cost"],
        )

        # Create order items from cart
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product_variant=item.product_variant,
                quantity=item.quantity
            )

        
        order.total_price = order.calculate_total()
        order.save(update_fields=["total_price"])

        cart.items.all().delete()
        cart.delete()

        return Response({
            "order_reference": order.order_reference,
            "total_price": order.total_price
        }, status=status.HTTP_201_CREATED)


class UserOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.prefetch_related('items').filter(user=request.user).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)