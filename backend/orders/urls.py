from django.urls import path
from .views import CreateOrderView, UserOrdersView, StripeWebhookView, ExecutePayPalPaymentView, VerifyStripePaymentView

urlpatterns = [
    path('orders/create/', CreateOrderView.as_view(), name='create-order'),
    path('webhook/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('orders/my/', UserOrdersView.as_view(), name='user-orders'),
    path('stripe/verify-payment/', VerifyStripePaymentView.as_view(), name='stripe-verify-payment'),
    path('paypal/execute/', ExecutePayPalPaymentView.as_view(), name='paypal-execute'),
]