from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Collection, ProductVariant, ProductColorImage, Color, Size, Categories
from .serializers import (
    ProductSerializer,
    CollectionSerializer,
    CollectionDetailSerializer,
    CategoriesSerializer,
    ProductListFilteredSerializer,
    SizeSerializer,
    ColorSerializer
)
from django.db.models import Prefetch
from .filters import ProductFlatFilter, CollectionFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination



class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10                  # default items per page
    page_size_query_param = 'page_size'
    max_page_size = 100

class CollectionListView(generics.ListAPIView):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CollectionFilter

class ColorListView(generics.ListAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer

class SizeListView(generics.ListAPIView):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer

class CategoriesListView(generics.ListAPIView):
    queryset = Categories.objects.all()
    serializer_class = CategoriesSerializer

class CollectionDetailView(generics.RetrieveAPIView):
    queryset = Collection.objects.all()
    serializer_class = CollectionDetailSerializer
    lookup_field = 'slug'

class ProductDetailWithVariantView(APIView):
    def get(self, request, slug, variant_slug):
        product = get_object_or_404(
            Product.objects.prefetch_related('variants__color', 'variants__size')
            .select_related('collection'),
            slug=slug
        )
        variant = get_object_or_404(ProductVariant, slug=variant_slug, product=product)

        serializer = ProductSerializer(product, context={'variant_id': variant.slug})
        return Response(serializer.data)

class ProductFilteredListView(generics.ListAPIView):
    queryset = (
        Product.objects
        .select_related('collection')
        .prefetch_related(
            Prefetch(
                'color_images',
                queryset=ProductColorImage.objects.select_related('color'),
            ),
            Prefetch(
                'variants',
                queryset=ProductVariant.objects
                    .select_related('size', 'color', 'color__color'),
            ),
        )
        .distinct()
    )
    serializer_class = ProductListFilteredSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends  = [DjangoFilterBackend]
    filterset_class  = ProductFlatFilter