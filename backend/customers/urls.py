from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import RegisterView, CustomerMeView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='customer-register'),
    path('login/', TokenObtainPairView.as_view(), name='customer-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='customer-token-refresh'),
    path('me/', CustomerMeView.as_view(), name='customer-me'),
]
