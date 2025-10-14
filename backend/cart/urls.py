from django.urls import path
from .views import CartView, UpdateCartItemView, DeleteCartItemView, ClearCartView

urlpatterns = [
    path('cart/', CartView.as_view()),  # GET only
    path('cart/item/', UpdateCartItemView.as_view()),  # PUT
    path('cart/item/delete/', DeleteCartItemView.as_view()),  # DELETE single item
    path('cart/clear/', ClearCartView.as_view()),  # DELETE all items
]