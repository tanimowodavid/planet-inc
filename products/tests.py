from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Category, Product, ProductVariant

User = get_user_model()


class CategoryModelTests(TestCase):
    """Test Category model"""

    def test_create_category(self):
        """Test creating a category"""
        category = Category.objects.create(
            name='Action Figures',
            description='Premium action figures for collectors'
        )
        self.assertEqual(category.name, 'Action Figures')
        self.assertEqual(category.slug, 'action-figures')

    def test_category_slug_generated_automatically(self):
        """Test that slug is generated from name"""
        category = Category.objects.create(
            name='Premium Bicycles'
        )
        self.assertEqual(category.slug, 'premium-bicycles')

    def test_slug_is_unique(self):
        """Test that slug is unique"""
        Category.objects.create(name='Toys')
        with self.assertRaises(Exception):
            Category.objects.create(name='Toys')

    def test_category_with_parent(self):
        """Test creating subcategory"""
        parent = Category.objects.create(name='Vehicles')
        child = Category.objects.create(
            name='Bicycles',
            parent=parent
        )
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.subcategories.all())


class ProductModelTests(TestCase):
    """Test Product model core functionality"""

    def setUp(self):
        self.category = Category.objects.create(name='Action Figures')

    def test_active_manager(self):
        """Test that ActiveManager filters inactive products"""
        active_product = Product.objects.create(
            name='Active Product',
            description='Test',
            is_active=True
        )
        inactive_product = Product.objects.create(
            name='Inactive Product',
            description='Test',
            is_active=False
        )
        # Using default 'objects' manager (ActiveManager)
        active_list = Product.objects.all()
        self.assertIn(active_product, active_list)
        self.assertNotIn(inactive_product, active_list)

    def test_all_objects_manager(self):
        """Test that all_objects manager returns all products"""
        active = Product.objects.create(name='Active', description='Test', is_active=True)
        inactive = Product.objects.create(name='Inactive', description='Test', is_active=False)
        
        all_list = Product.all_objects.all()
        self.assertIn(active, all_list)
        self.assertIn(inactive, all_list)

    def test_product_embedding_generation(self):
        """Test that embedding is generated on save"""
        product = Product.objects.create(
            name='Test Product',
            description='Test description'
        )
        self.assertIsNotNone(product.embedding)


class ProductVariantModelTests(TestCase):
    """Test ProductVariant model core functionality"""

    def setUp(self):
        self.product = Product.objects.create(
            name='Action Figure',
            description='A collectible figure'
        )

    def test_variant_sku_unique(self):
        """Test that SKU is unique"""
        variant1 = ProductVariant.objects.create(
            product=self.product,
            variant_name='Edition 1',
            price=29.99,
            stock_quantity=50
        )
        variant2 = ProductVariant.objects.create(
            product=self.product,
            variant_name='Edition 2',
            price=29.99,
            stock_quantity=50
        )
        self.assertNotEqual(variant1.sku, variant2.sku)

    def test_variant_active_manager(self):
        """Test that active variants are filtered"""
        active = ProductVariant.objects.create(
            product=self.product,
            variant_name='Active',
            price=29.99,
            stock_quantity=50,
            is_active=True
        )
        inactive = ProductVariant.objects.create(
            product=self.product,
            variant_name='Inactive',
            price=29.99,
            stock_quantity=50,
            is_active=False
        )
        active_list = ProductVariant.objects.all()
        self.assertIn(active, active_list)
        self.assertNotIn(inactive, active_list)


class CategoryAPITests(APITestCase):
    """Test Category API endpoints"""

    def setUp(self):
        # Create an admin user
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='adminpass',
            first_name='Admin',
            last_name='User',
            is_staff=True,
            is_superuser=True
        )
        self.client = APIClient()

    def test_create_category_as_admin(self):
        """Test creating a category as admin"""
        self.client.force_authenticate(user=self.admin)
        data = {
            'name': 'Collectibles',
            'description': 'Collectible items'
        }
        response = self.client.post('/api/products/admin/categories/create/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Collectibles')

    def test_create_category_unauthorized(self):
        """Test creating a category without admin access"""
        data = {
            'name': 'Toys',
            'description': 'Toy items'
        }
        response = self.client.post('/api/products/admin/categories/create/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ProductAPITests(APITestCase):
    """Test Product API endpoints"""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='adminpass',
            first_name='Admin',
            last_name='User',
            is_staff=True,
            is_superuser=True
        )
        self.category = Category.objects.create(name='Figures')
        self.product = Product.objects.create(
            name='Test Product',
            description='Test description'
        )
        self.product.category.add(self.category)
        self.client = APIClient()

    def test_create_product_as_admin(self):
        """Test creating a product as admin"""
        self.client.force_authenticate(user=self.admin)
        data = {
            'name': 'New Product',
            'description': 'Product description',
            'category': [self.category.id]
        }
        response = self.client.post('/api/products/admin/products/create/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_product_unauthorized(self):
        """Test creating a product without admin access"""
        data = {
            'name': 'New Product',
            'description': 'Product description'
        }
        response = self.client.post('/api/products/admin/products/create/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_product_as_admin(self):
        """Test updating a product as admin"""
        self.client.force_authenticate(user=self.admin)
        data = {
            'name': 'Updated Product',
            'description': 'Updated description'
        }
        response = self.client.put(f'/api/products/admin/products/{self.product.slug}/update/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated Product')

    def test_list_variants_public(self):
        """Test listing product variants (public endpoint)"""
        variant = ProductVariant.objects.create(
            product=self.product,
            variant_name='Standard',
            price=29.99,
            stock_quantity=50
        )
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_get_variant_detail(self):
        """Test getting a specific variant"""
        variant = ProductVariant.objects.create(
            product=self.product,
            variant_name='Standard',
            price=29.99,
            stock_quantity=50
        )
        response = self.client.get(f'/api/products/{variant.sku}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sku'], variant.sku)

    def test_get_nonexistent_variant(self):
        """Test getting a non-existent variant"""
        response = self.client.get('/api/products/nonexistent-sku/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

