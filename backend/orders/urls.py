from django.urls import path
from .views import CreateOrderView, UserOrdersView

urlpatterns = [
    path('orders/create/', CreateOrderView.as_view(), name='create-order'),
    path('orders/my/', UserOrdersView.as_view(), name='user-orders'),
]