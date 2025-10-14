from django.urls import path
from .views import (
    ProductListView,
    ProductDetailWithVariantView,
    CollectionListView,
    CollectionDetailView,
    ProductFilteredListView,
    ColorListView,
    SizeListView,
    CategoriesListView
)

urlpatterns = [
    path('products/', ProductListView.as_view(), name='product-list'),
    path('colors/', ColorListView.as_view(), name='color-list'),
    path('sizes/', SizeListView.as_view(), name='size-list'),
    path('categories/', CategoriesListView.as_view(), name='categories-list'),
    path('collections/', CollectionListView.as_view(), name='collection-list'),
    path('collections/<slug:slug>/', CollectionDetailView.as_view(), name='collection-detail'),
    path('products/<slug:slug>/<slug:variant_slug>/', ProductDetailWithVariantView.as_view(), name='product-detail-with-variant'),
    path('products-all/', ProductFilteredListView.as_view(), name='product-detail'),
]
