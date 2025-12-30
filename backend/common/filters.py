from django_filters import rest_framework as filters
from .models import Product, Collection,Size, Color
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


class ProductFlatFilter(django_filters.FilterSet):
    collection = django_filters.CharFilter(
        field_name='collection__slug',
        lookup_expr='exact'
    )
    
    # Changed to filter by category name instead of ID
    category = django_filters.CharFilter(
        method='filter_categories',
        label='Category'
    )
    
    gender = django_filters.CharFilter(
        field_name='gender',
        lookup_expr='exact'
    )
    
    size = django_filters.CharFilter(
        method='filter_sizes',
        label='Size'
    )
    
    color = django_filters.CharFilter(
        method='filter_colors',
        label='Color'
    )

    class Meta:
        model = Product
        fields = ['collection', 'category', 'gender', 'size', 'color']

    def filter_categories(self, queryset, name, value):
        """
        Filter products that belong to ANY of the specified category names
        """
        if not value:
            return queryset
        
        # Get all category names from query params
        category_names = self.request.GET.getlist('category')
        if not category_names:
            return queryset
        
        # Filter by category name instead of ID
        return queryset.filter(
            category__name__in=category_names
        ).distinct()

    def filter_sizes(self, queryset, name, value):
        if not value:
            return queryset
        
        sizes = self.request.GET.getlist('size')
        if not sizes:
            return queryset
        
        return queryset.filter(
            variants__size__name__in=sizes
        ).distinct()

    def filter_colors(self, queryset, name, value):
        if not value:
            return queryset
        
        colors = self.request.GET.getlist('color')
        if not colors:
            return queryset
        
        return queryset.filter(
            color_images__color__name__in=colors
        ).distinct()
    