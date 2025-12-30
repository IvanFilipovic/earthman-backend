from django.contrib import admin
from .models import Collection, Color, Size, Product, ProductVariant, ProductVariantImage, ProductColorImage, Categories
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin

class ProductVariantResource(resources.ModelResource):
    product = fields.Field(
        column_name='product',
        attribute='product',
        widget=ForeignKeyWidget(Product, 'name'),
    )
    size = fields.Field(
        column_name='size',
        attribute='size',
        widget=ForeignKeyWidget(Size, 'name'),
    )
    color = fields.Field(
        column_name='color',
        attribute='color',
        widget=ForeignKeyWidget(ProductColorImage, 'name'),
    )

    class Meta:
        model = ProductVariant
        fields = ('id', 'product', 'color', 'size', 'available', 'slug')
        export_order = ('id', 'product', 'color', 'size', 'available', 'slug')

    def dehydrate_color(self, obj):
        return obj.color.color.name if obj.color and obj.color.color else ""
    

class ProductColorResource(resources.ModelResource):
    color = fields.Field(column_name='color', attribute='color', widget=ForeignKeyWidget(Color, 'name'))
    product = fields.Field(column_name='product', attribute='product', widget=ForeignKeyWidget(Product, 'name'))

    class Meta:
        model = ProductColorImage

class ProductResource(resources.ModelResource):
    collection = fields.Field(column_name='collection', attribute='collection', widget=ForeignKeyWidget(Collection, 'name'))

    class Meta:
        model = Product
# Register the Collection model
@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')  # Display name and slug in the admin list view
    prepopulated_fields = {'slug': ('name',)}  # Automatically generate slug from name
    search_fields = ('name',)  # Enable search by name

# Register the Color model
@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name',)  # Display color name in the admin list view
    search_fields = ('name',)  # Enable search by name

# Register the Size model
@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name',)  # Display size name in the admin list view
    search_fields = ('name',)  # Enable search by name

@admin.register(Categories)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)  # Display category name in the admin list view
    search_fields = ('name',)  # Enable search by name

class ProductColorImageInline(admin.TabularInline):
    model = ProductColorImage
    extra = 1
    fields = ('color', 'avatar_image', 'alt_text')
    
class ProductVariantImageInline(admin.TabularInline):
    model = ProductVariantImage
    extra = 1
    max_num = 10
    fields = ('image', 'alt_text')


# Inline for variants under Product admin
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('color', 'size', 'available') 


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ('name', 'price', 'collection', 'available', 'slug')
    list_filter = ('collection',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductColorImageInline, ProductVariantInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(ImportExportModelAdmin):
    resource_class = ProductVariantResource
    list_display = ('product', 'color', 'size', 'available')

@admin.register(ProductColorImage)
class ProductColorImageAdmin(ImportExportModelAdmin):
    resource_class = ProductColorResource
    list_display = ('product', 'color', 'name', 'avatar_image')
    list_filter = ('product', 'color')
    search_fields = (
        'product__name',     # search by Product name
        'color__name',       # search by Color name
        'name',              # internal PCI name
        'alt_text',          # alt text
        'avatar_image',      # URL contains…
    )
    inlines = [ProductVariantImageInline]

    # (optional – nice UX) quick jump to related objects
    autocomplete_fields = ('product', 'color')

@admin.register(ProductVariantImage)
class ProductVariantImageAdmin(admin.ModelAdmin):
    pass