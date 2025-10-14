from django_filters import rest_framework as filters
from .models import Product, Collection
import django_filters

class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass

class ProductFilter(filters.FilterSet):
    collection = filters.CharFilter(field_name='collection__slug', lookup_expr='iexact')
    available = filters.BooleanFilter()

    class Meta:
        model = Product
        fields = ['collection', 'available']

class CollectionFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr='icontains')
    slug = filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = Collection
        fields = ['name', 'slug']

class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    """Accepts comma-separated values or repeated ?param=...&param=..."""
    pass

class ProductFlatFilter(filters.FilterSet):
    # Basic fields
    collection = filters.CharFilter(field_name='collection__slug')
    gender = filters.CharFilter(field_name='gender', lookup_expr='iexact')

    available  = filters.BooleanFilter(field_name='available')
    min_price  = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price  = filters.NumberFilter(field_name='price', lookup_expr='lte')

    # Multi-category OR (any)
    category   = CharInFilter(field_name='category', lookup_expr='in')

    # Colors (via ProductColorImage -> Color.name)
    # OR (any): ?color=Blue,White or ?color=Blue&color=White
    color      = CharInFilter(field_name='color_images__color__name', lookup_expr='in')

    # Sizes (via Variant.size.name)
    # OR (any): ?size=S,M,XL
    size       = CharInFilter(field_name='variants__size__name', lookup_expr='in')

    # AND (all) semantics for sizes: ?size_all=S,XXL
    size_all   = filters.CharFilter(method='filter_sizes_all')

    # Product-level flags (not on variants)
    hot        = filters.BooleanFilter(field_name='hot')
    new        = filters.BooleanFilter(field_name='new')

    class Meta:
        model  = Product
        fields = [
            'collection', 'available',
            'min_price', 'max_price',
            'category', 'color', 'size', 'size_all', 'gender',
            'hot', 'new',
        ]

    def filter_sizes_all(self, qs, name, value):
        """
        AND semantics for comma-separated sizes.
        Requires product to have variants in *all* requested sizes (any color).
        """
        if not value:
            return qs
        sizes = [s.strip() for s in value.split(',') if s.strip()]
        for s in sizes:
            qs = qs.filter(variants__size__name__iexact=s)
        return qs.distinct()