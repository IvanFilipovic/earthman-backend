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
        # Step 1: Check for existing cart_session_id in cookies
        session_id = request.COOKIES.get(settings.CART_SESSION_COOKIE)

        # Step 2: If session_id doesn't exist, create a new cart and set the cookie
        if not session_id:
            # Generate a new session ID
            session_id = str(uuid.uuid4())

            # Create a new Cart with the session ID
            cart = Cart.objects.create(session_id=session_id)
            
            # Step 3: Set the cookie for future requests
            response = Response({"detail": "New cart created."}, status=status.HTTP_201_CREATED)

            # Set the cookie in the response (this is the important part)
            response.set_cookie(
                key=settings.CART_SESSION_COOKIE,
                value=session_id,
                max_age=settings.CART_COOKIE_AGE,  # 7 days
                httponly=False,  # Set to True to make it inaccessible from JavaScript
                samesite='None',  # 'Strict' or 'Lax' for security, 'None' for cross-site requests
                secure=True,  # Set to True in production (HTTPS)
                path='/',  # Ensure the cookie is available on all paths
            )
            return response
        else:
            # Step 4: Try to find an existing cart if session_id exists
            try:
                cart = Cart.objects.get(session_id=session_id)
                serializer = CartSerializer(cart)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Cart.DoesNotExist:
                # If cart doesn't exist with that session ID
                return Response({"detail": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)

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

        if not quantity or int(quantity) < 1:
            return Response({"detail": "Quantity must be 1 or more."}, status=status.HTTP_400_BAD_REQUEST)

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
