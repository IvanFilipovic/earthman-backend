import uuid
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Cart, CartItem
from common.models import ProductVariant
from .serializers import CartSerializer

class CartView(APIView):
    def get(self, request):
        session_id = request.COOKIES.get(settings.CART_SESSION_COOKIE)
        if not session_id:
            return Response({"detail": "Missing cart session cookie."}, status=status.HTTP_400_BAD_REQUEST)

        cart, _ = Cart.objects.get_or_create(session_id=session_id)
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class UpdateCartItemView(APIView):
    def put(self, request):
        session_id = request.COOKIES.get(settings.CART_SESSION_COOKIE)
        if not session_id:
            return Response({"detail": "Session ID not found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(session_id=session_id)
        except Cart.DoesNotExist:
            return Response({"detail": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)

        product_variant_slug = request.data.get("product_variant_slug")
        quantity = request.data.get("quantity")

        if not product_variant_slug:
            return Response({"detail": "Missing product_variant_slug."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate quantity with upper and lower limits
        try:
            quantity = int(quantity)
            if quantity < 1 or quantity > 999:
                return Response(
                    {"detail": "Quantity must be between 1 and 999."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid quantity format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            variant = ProductVariant.objects.get(slug=product_variant_slug)
        except ProductVariant.DoesNotExist:
            return Response({"detail": "Product variant not found."}, status=status.HTTP_404_NOT_FOUND)

        # Create or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product_variant=variant,
            defaults={"quantity": quantity}
        )

        if not created:
            cart_item.quantity = quantity
            cart_item.save()

        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)
        
class DeleteCartItemView(APIView):
    def delete(self, request):
        session_id = request.COOKIES.get(settings.CART_SESSION_COOKIE)
        if not session_id:
            return Response({"detail": "Session ID not found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(session_id=session_id)
            product_variant_slug = request.data.get("product_variant_slug")

            cart_item = CartItem.objects.get(cart=cart, product_variant__slug=product_variant_slug)
            cart_item.delete()

            return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)

        except Cart.DoesNotExist:
            return Response({"detail": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)
        except CartItem.DoesNotExist:
            return Response({"detail": "Cart item not found."}, status=status.HTTP_404_NOT_FOUND)

class ClearCartView(APIView):
    def delete(self, request):
        session_id = request.COOKIES.get(settings.CART_SESSION_COOKIE)
        if not session_id:
            return Response({"detail": "Session ID not found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(session_id=session_id)
            cart.items.all().delete()

            return Response({"detail": "Cart cleared."}, status=status.HTTP_200_OK)

        except Cart.DoesNotExist:
            return Response({"detail": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)
