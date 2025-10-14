from rest_framework import serializers
from .models import (
    Product,
    ProductVariant,
    ProductVariantImage,
    Collection,
    Color,
    Size,
    Categories,
    ProductColorImage
)

class CollectionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = '__all__'

class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ['name', 'image', 'alt_text']

class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ['name']

class CategoriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = ["id", 'name']


class ProductVariantImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariantImage
        fields = ['id', 'image', 'alt_text']


class ProductVariantShortSerializer(serializers.ModelSerializer):
    size = SizeSerializer()

    class Meta:
        model = ProductVariant
        fields = ['slug', 'size', 'available']


class ProductVariantDetailSerializer(serializers.ModelSerializer):
    color = ColorSerializer()
    size = SizeSerializer()
    images = ProductVariantImageSerializer(many=True)

    class Meta:
        model = ProductVariant
        fields = ['slug', 'color', 'size', 'available', 'images']


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    collection_slug = serializers.SlugRelatedField(source='collection', read_only=True, slug_field='slug')
    variant_groups = serializers.SerializerMethodField()
    selected_variant = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'category', 'slug', 'description', 'price', 'discount',
            'discount_price',
            'collection_slug', 'created_at', 'updated_at', 'available',
            'variant_groups', 'selected_variant'
        ]

    def get_variant_groups(self, obj):
        from collections import defaultdict
        grouped = defaultdict(list)

        # IMPORTANT: variant.color is ProductColorImage; its Color is variant.color.color
        # Preload color->color and size to avoid N+1
        for variant in obj.variants.select_related('color__color', 'size'):
            grouped[variant.color.color_id].append(variant)  # group by Color id

        result = []
        for variants in grouped.values():
            pci = variants[0].color                  # ProductColorImage
            color_obj = pci.color                    # Color
            avatar_image = pci.avatar_image          # URL or None

            result.append({
                'color': ColorSerializer(color_obj).data,
                'avatar_image': avatar_image,
                'sizes': ProductVariantShortSerializer(variants, many=True).data
            })

        return result

    def get_selected_variant(self, obj):
        variant_slug = self.context.get('variant_id')  # name suggests id, but it's a slug
        if not variant_slug:
            return None
        try:
            # preload nested color->color and images
            variant = (
                obj.variants
                  .select_related('color__color', 'size')
                  .prefetch_related('images')
                  .get(slug=variant_slug)
            )
            return ProductVariantDetailSerializer(variant).data
        except ProductVariant.DoesNotExist:
            return None

class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'price']


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ['id', 'name', 'slug', 'element_one', 'element_one_image',]


class ProductListFlatSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.SlugField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount = serializers.BooleanField()
    color = serializers.CharField()
    variant_slug = serializers.SlugField()
    avatar_image = serializers.URLField(allow_null=True, required=False)
    link_image = serializers.ImageField(allow_null=True, required=False)

class ProductListWithColorsSerializer(serializers.ModelSerializer):
    colors = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "description",
            "price", "discount", "discount_price",
            "category", "available",
            "colors", "link_image", "alt_text"
        ]

    def get_colors(self, product):
        out = []
        # We assume you've prefetched `color_images__color` and `variants__color`
        for ci in product.color_images.all():
            variant = product.variants.filter(color=ci.color).first()
            out.append({
                "color":        ci.color.name,
                "avatar_image": ci.avatar_image,
                "variant_slug": variant.slug if variant else None,
            })
        return out
    
class ProductListFilteredSerializer(serializers.ModelSerializer):
    colors = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "gender",
            "price", "discount", "discount_price",
            "category", "available", "link_image", "alt_text",
            "colors",
        ]

    def get_colors(self, product):
        """
        Return ALL colors the product has.
        Pick a representative variant slug per color (any size).
        Assumes variants/color_images are prefetched.
        """
        # Build an index: PCI.id -> first variant slug we find
        rep_by_pci = {}
        for v in product.variants.all():
            pci_id = v.color_id
            if pci_id not in rep_by_pci and v.slug:
                rep_by_pci[pci_id] = v.slug

        out = []
        for ci in product.color_images.all():      # ci is ProductColorImage
            slug = rep_by_pci.get(ci.id, "")
            out.append({
                "color":        ci.color.name,
                "avatar_image": ci.avatar_image or "",
                "variant_slug": slug,
            })
        return out