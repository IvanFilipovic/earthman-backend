# orders/views.py

import stripe
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from .emails import send_order_emails, send_payment_failed_emails
from .models import Order, OrderItem
from .serializers import OrderSerializer
from .paypal_helper import create_paypal_order, execute_paypal_payment
from cart.models import Cart
from customers.models import Guest

stripe.api_key = settings.STRIPE_SECRET_KEY


class CreateOrderView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Get session ID
        session_id = request.COOKIES.get(settings.CART_SESSION_COOKIE)
        if not session_id:
            session_id = request.data.get('session_id')
        
        if not session_id:
            return Response(
                {"detail": "Session not found. Please add items to cart first."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get cart
        try:
            cart = Cart.objects.prefetch_related(
                'items__product_variant__product'
            ).get(session_id=session_id)
            
            if not cart.items.exists():
                return Response(
                    {"detail": "Cart is empty."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Cart.DoesNotExist:
            return Response(
                {"detail": "Cart not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Extract customer data
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
        }

        # Validate required fields
        required_fields = ["email", "address", "city", "postal_code", "phone_number", "payment_method"]
        if not all([customer_data.get(k) for k in required_fields]):
            return Response(
                {"detail": "Missing required customer fields."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create user/guest
        user = request.user if request.user.is_authenticated else None
        guest = None

        if not user:
            guest, _ = Guest.objects.get_or_create(email=customer_data["email"])

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
            payment_status='pending'
        )

        # Create order items from cart
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product_variant=item.product_variant,
                quantity=item.quantity
            )

        # Calculate total
        order.total_price = order.calculate_total()
        order.save(update_fields=["total_price"])

        # Prepare response
        response_data = {
            "order_reference": order.order_reference,
            "total_price": str(order.total_price),
            "payment_method": order.payment_method,
        }

        # Handle payment methods
        if customer_data["payment_method"] == "card":
            # Stripe Payment
            try:
                payment_intent = stripe.PaymentIntent.create(
                    amount=int(order.total_price * 100),  # Convert to cents
                    currency='eur',
                    metadata={
                        'order_reference': order.order_reference,
                        'customer_email': customer_data["email"],
                        'cart_session_id': session_id,  # Store for webhook
                    },
                    description=f"Order {order.order_reference}",
                )

                order.stripe_payment_intent_id = payment_intent.id
                order.stripe_client_secret = payment_intent.client_secret
                order.payment_status = 'processing'
                order.save(update_fields=[
                    'stripe_payment_intent_id', 
                    'stripe_client_secret', 
                    'payment_status'
                ])

                response_data["client_secret"] = order.stripe_client_secret

            except stripe.error.StripeError as e:
                # Delete order if Stripe fails
                order.delete()
                return Response(
                    {"detail": f"Stripe error: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        elif customer_data["payment_method"] == "paypal":
            # PayPal Payment
            paypal_result = create_paypal_order(
                order_reference=order.order_reference,
                total_amount=float(order.total_price),
                currency='EUR'
            )

            if paypal_result['success']:
                order.paypal_order_id = paypal_result['payment_id']
                order.payment_status = 'processing'
                order.save(update_fields=['paypal_order_id', 'payment_status'])

                response_data["paypal_approval_url"] = paypal_result['approval_url']
                response_data["paypal_payment_id"] = paypal_result['payment_id']
            else:
                # Delete order if PayPal fails
                order.delete()
                return Response(
                    {"detail": f"PayPal error: {paypal_result.get('error')}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        else:
            # Other payment methods (cash on delivery, etc.)
            pass


        return Response(response_data, status=status.HTTP_201_CREATED)


class VerifyStripePaymentView(APIView):
    """Verify Stripe payment status for an order"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        payment_intent_id = request.data.get('payment_intent_id')
        order_reference = request.data.get('order_reference')
        
        if not payment_intent_id or not order_reference:
            return Response({
                'success': False,
                'error': 'Missing payment_intent_id or order_reference'
            }, status=400)
        
        try:
            order = Order.objects.get(order_reference=order_reference)
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if payment_intent.status == 'succeeded':
                # Update order status if not already paid
                if order.payment_status != 'paid':
                    order.payment_status = 'paid'
                    order.transaction_id = payment_intent_id
                    order.save(update_fields=['payment_status', 'transaction_id'])
                    
                    # Delete cart
                    cart_session_id = payment_intent.metadata.get('cart_session_id')
                    if cart_session_id:
                        try:
                            cart = Cart.objects.get(session_id=cart_session_id)
                            cart.items.all().delete()
                            cart.delete()
                            print(f"✅ Cart deleted for order {order_reference}")
                        except Cart.DoesNotExist:
                            print(f"⚠️ Cart already deleted for {order_reference}")
                
                # ✅ Send emails (will check if already sent)
                send_order_emails(order)
                
                return Response({
                    'success': True,
                    'order_reference': order.order_reference,
                    'total_price': str(order.total_price),
                    'payment_status': order.payment_status
                })
            else:
                order.payment_status = 'failed'
                order.save(update_fields=['payment_status'])
                send_payment_failed_emails(order)
                
                return Response({
                    'success': False,
                    'error': f'Payment status is {payment_intent.status}',
                    'payment_status': payment_intent.status
                }, status=400)
                
        except Order.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Order not found'
            }, status=404)
        except stripe.error.StripeError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=400)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Verification failed'
            }, status=500)


class StripeWebhookView(APIView):
    """Handle Stripe webhook events"""
    permission_classes = [AllowAny]

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse(status=400)

        # Handle payment_intent.succeeded event
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            order_reference = payment_intent['metadata'].get('order_reference')
            cart_session_id = payment_intent['metadata'].get('cart_session_id')
            
            try:
                order = Order.objects.get(order_reference=order_reference)
                
                # Update order status if not already paid
                if order.payment_status != 'paid':
                    order.payment_status = 'paid'
                    order.transaction_id = payment_intent.id
                    order.save(update_fields=['payment_status', 'transaction_id'])
                
                # Delete cart if not already deleted
                if cart_session_id:
                    try:
                        cart = Cart.objects.get(session_id=cart_session_id)
                        cart.items.all().delete()
                        cart.delete()
                        print(f"✅ Cart deleted for order {order_reference}")
                    except Cart.DoesNotExist:
                        print(f"⚠️ Cart already deleted for {order_reference}")
                
                # ✅ Send emails (will check if already sent)
                send_order_emails(order)
                
            except Order.DoesNotExist:
                return HttpResponse(status=404)

        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            order_reference = payment_intent['metadata'].get('order_reference')
            
            try:
                order = Order.objects.get(order_reference=order_reference)
                order.payment_status = 'failed'
                order.save(update_fields=['payment_status'])
                
                send_payment_failed_emails(order)
                
            except Order.DoesNotExist:
                return HttpResponse(status=404)

        return HttpResponse(status=200)


class ExecutePayPalPaymentView(APIView):
    """Execute PayPal payment after user approval"""
    permission_classes = [AllowAny]

    def post(self, request):
        payment_id = request.data.get('payment_id')
        payer_id = request.data.get('payer_id')
        order_reference = request.data.get('order_reference')

        if not all([payment_id, payer_id, order_reference]):
            return Response(
                {"detail": "Missing payment parameters"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = Order.objects.get(order_reference=order_reference)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Execute PayPal payment
        result = execute_paypal_payment(payment_id, payer_id)

        if result['success']:
            # Update order status
            order.payment_status = 'paid'
            order.paypal_payer_id = payer_id
            order.transaction_id = payment_id
            order.save(update_fields=[
                'payment_status', 
                'paypal_payer_id', 
                'transaction_id'
            ])

            # ✅ Send emails (will check if already sent)
            send_order_emails(order)
            
            # Clean up cart
            try:
                if order.guest:
                    carts = Cart.objects.filter(items__isnull=False).distinct()
                    for cart in carts:
                        cart.items.all().delete()
                        cart.delete()
                        print(f"✅ Cart deleted for PayPal order {order_reference}")
                        break
            except Exception as e:
                print(f"⚠️ Could not delete cart: {e}")

            return Response({
                "success": True,
                "order_reference": order.order_reference,
                "total_price": str(order.total_price)
            }, status=status.HTTP_200_OK)
        
        else:
            order.payment_status = 'failed'
            order.save(update_fields=['payment_status'])
            send_payment_failed_emails(order)
            
            return Response(
                {"detail": f"Payment execution failed: {result.get('error')}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
class UserOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.prefetch_related('items').filter(
            user=request.user
        ).order_by('-created_at')
        
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)