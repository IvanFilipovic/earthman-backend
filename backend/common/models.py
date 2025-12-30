import uuid
from django.db import models

def generate_slug(collectionshort):
    return f"{collectionshort[:3].upper()}-{uuid.uuid4().hex[:8].upper()}"

# Model za kolekcije
class Collection(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    element_one_image = models.URLField(max_length=200, blank=True, null=True)
    element_one = models.TextField(blank=True, null=True)
    element_two = models.TextField(blank=True, null=True)
    element_two_image = models.URLField(max_length=200, blank=True, null=True)
    element_three = models.TextField(blank=True, null=True)
    element_three_image = models.URLField(max_length=200, blank=True, null=True)
    element_four = models.TextField(blank=True, null=True)
    element_four_image = models.URLField(max_length=200, blank=True, null=True)
    element_five = models.TextField(blank=True, null=True)
    element_five_image = models.URLField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name

# Model za boje
class Color(models.Model):
    name = models.CharField(max_length=50)
    image = models.CharField(max_length=16, blank=True, null=True)
    alt_text = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return self.name

# Model za veličine
class Size(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

# Model za kategorije
class Categories(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        verbose_name = "category"
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

# Model za proizvode
class Product(models.Model):
    GENDER = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('kid', 'Kids'),
    ]
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name="products", blank=True, null=True)
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name="categories", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    available = models.BooleanField(default=True)
    discount = models.BooleanField(default=False)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER, blank=True, null=True)
    alt_text = models.CharField(max_length=128, blank=True)
    link_image = models.URLField(max_length=200, blank=True, null=True)
    hot = models.BooleanField(default=False)
    new = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
class ProductColorImage(models.Model):
    name = models.CharField(max_length=60, blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='color_images')
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    avatar_image = models.URLField(max_length=200, blank=True, null=True)
    alt_text = models.CharField(max_length=128, blank=True)

    class Meta:
        unique_together = ('product', 'color')

    def __str__(self):
        return f"{self.name}"
    
# Model za varijante proizvoda
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    slug = models.SlugField(unique=True, null=True, blank=True)
    color = models.ForeignKey(ProductColorImage, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    available = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            collection_name = self.product.collection.name if self.product and self.product.collection else "COL"
            self.slug = generate_slug(collection_name)
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('product', 'color', 'size')

    def __str__(self):
        return f"{self.product.name} - {self.color.color} - {self.size.name}"

# -- Product Variant Images --
class ProductVariantImage(models.Model):
    variant = models.ForeignKey(ProductColorImage, on_delete=models.CASCADE, related_name='images')
    image = models.URLField(max_length=200, blank=True, null=True)
    alt_text = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return f"Image for {self.variant}"

