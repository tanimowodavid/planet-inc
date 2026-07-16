import uuid
from django.db import models
from .managers import ActiveManager
from django.utils.text import slugify
from pgvector.django import VectorField
from .utils import generate_product_embedding

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True , blank=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.ManyToManyField(Category, related_name='products', blank=True)
    embedding = VectorField(dimensions=1536, null=True, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            unique_slug = base_slug
            
            while Product.all_objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"
            
            self.slug = unique_slug
        # Generate embedding if it doesn't exist or if description changed
        if not self.embedding:
            combined_text = f"{self.name}: {self.description}"
            self.embedding = generate_product_embedding(combined_text)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name




class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='variants')
    sku = models.CharField(max_length=100, unique=True)
    variant_name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['is_active']),
        ]

    def save(self, *args, **kwargs):
        if not self.sku:
            product_part = slugify(self.product.name)[:3].upper()
            variant_part = slugify(self.variant_name)[:3].upper()
            
            unique_id = str(uuid.uuid4())[:4].upper()
            self.sku = f"{product_part}-{variant_part}-{unique_id}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.variant_name}"

