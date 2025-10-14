import sys
from urllib import request
from urllib.request import Request
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Collection, ProductVariant, ProductColorImage, Color, Size, Categories
from .serializers import (
    ProductSerializer,
    CollectionSerializer,
    CollectionDetailSerializer,
    CategoriesSerializer,
    ProductListWithColorsSerializer,
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
            Product.objects.prefetch_related('variants__color', 'variants__size', 'variants__images')
            .select_related('collection'),
            slug=slug
        )
        variant = get_object_or_404(ProductVariant, slug=variant_slug, product=product)

        serializer = ProductSerializer(product, context={'variant_id': variant.slug})
        return Response(serializer.data)

class ProductListView(APIView):
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFlatFilter
    pagination_class   = StandardResultsSetPagination

    def get(self, request: Request):
        queryset = Product.objects.prefetch_related(
            'variants__color', 'variants__size'
        ).distinct()

        # Apply filters to product queryset
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(request, queryset, self)

        # Extract filtering params (for filtering variants inside each product)
        color_filter = request.query_params.get('color')
        size_filter = request.query_params.get('size')
        hot_filter = request.query_params.get('hot')
        new_filter = request.query_params.get('new')

        response_data = []

        for product in queryset:
            color_groups = {}

            # Filter variants manually
            filtered_variants = product.variants.all()
            if color_filter:
                filtered_variants = filtered_variants.filter(color__name__iexact=color_filter)
            if size_filter:
                filtered_variants = filtered_variants.filter(size__name__iexact=size_filter)
            if hot_filter is not None:
                filtered_variants = filtered_variants.filter(hot=hot_filter.lower() == 'true')
            if new_filter is not None:
                filtered_variants = filtered_variants.filter(new=new_filter.lower() == 'true')

            for variant in filtered_variants:
                color_id = variant.color.id
                if color_id not in color_groups:
                    color_groups[color_id] = variant

            for variant in color_groups.values():
                avatar_image = None
                link_image = None
                
                try:
                    image_obj = ProductColorImage.objects.get(product=variant.product, color=variant.color)
                    print(image_obj.avatar_image, file=sys.stderr)
                    avatar_image = image_obj.avatar_image
                except ProductColorImage.DoesNotExist:
                    pass

                response_data.append({
                    "id": product.id,
                    "name": product.name,
                    "slug": product.slug,
                    "price": product.price,
                    "discount": product.discount,
                    "discount_price": product.discount_price,
                    "color": variant.color.name,
                    "variant_slug": variant.slug,
                    "avatar_image": avatar_image,
                })
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(response_data, request, view=self)
        if page is not None:
            # returns a Response with { count, next, previous, results: [...] }
            return paginator.get_paginated_response(page)

        # fallback if pagination is disabled or not needed
        return Response(response_data)
    
class ProductListWithColorsView(generics.ListAPIView):
    """
    GET /public/products/?page=1&page_size=5
    """
    queryset = Product.objects.prefetch_related(
        'collection',
        'color_images__color',
        'variants__color'
    ).all()
    serializer_class = ProductListWithColorsSerializer
    pagination_class = StandardResultsSetPagination

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