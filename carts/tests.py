from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Cart, CartItem
from products.models import Product, ProductVariant

User = get_user_model()


class CartModelTests(TestCase):
    """Test Cart model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_cart_total_price_empty(self):
        """Test total price calculation for empty cart"""
        cart = Cart.objects.create(user=self.user)
        self.assertEqual(cart.total_price, 0)

    def test_cart_total_price_with_items(self):
        """Test total price calculation with items"""
        cart = Cart.objects.create(user=self.user)
        product = Product.objects.create(
            name='Test Product',
            description='Test'
        )
        variant = ProductVariant.objects.create(
            product=product,
            variant_name='Standard',
            price=10.00,
            stock_quantity=100
        )
        CartItem.objects.create(cart=cart, product_variant=variant, quantity=5)
        self.assertEqual(cart.total_price, 50.00)

    def test_cart_total_price_multiple_items(self):
        """Test total price with multiple items"""
        cart = Cart.objects.create(user=self.user)
        product1 = Product.objects.create(name='Product 1', description='Test')
        product2 = Product.objects.create(name='Product 2', description='Test')
        
        variant1 = ProductVariant.objects.create(
            product=product1,
            variant_name='V1',
            price=10.00,
            stock_quantity=100
        )
        variant2 = ProductVariant.objects.create(
            product=product2,
            variant_name='V2',
            price=20.00,
            stock_quantity=100
        )
        CartItem.objects.create(cart=cart, product_variant=variant1, quantity=2)
        CartItem.objects.create(cart=cart, product_variant=variant2, quantity=3)
        
        self.assertEqual(cart.total_price, 80.00)  # (2*10) + (3*20)


class CartItemModelTests(TestCase):
    """Test CartItem model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.cart = Cart.objects.create(user=self.user)
        self.product = Product.objects.create(
            name='Test Product',
            description='Test'
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name='Standard',
            price=25.00,
            stock_quantity=100
        )

    def test_cart_item_subtotal(self):
        """Test subtotal calculation"""
        item = CartItem.objects.create(
            cart=self.cart,
            product_variant=self.variant,
            quantity=4
        )
        self.assertEqual(item.subtotal, 100.00)  # 4 * 25

    def test_unique_cart_variant_constraint(self):
        """Test that duplicate cart-variant pairs are prevented"""
        CartItem.objects.create(
            cart=self.cart,
            product_variant=self.variant,
            quantity=1
        )
        # Attempting to create another with same cart and variant should fail
        with self.assertRaises(Exception):
            CartItem.objects.create(
                cart=self.cart,
                product_variant=self.variant,
                quantity=1
            )


class CartAPITests(APITestCase):
    """Test Cart API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.product = Product.objects.create(
            name='Test Product',
            description='Test'
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name='Standard',
            price=29.99,
            stock_quantity=100
        )

    def test_add_item_to_cart(self):
        """Test adding an item to cart"""
        data = {
            'variant_sku': self.variant.sku,
            'quantity': 2
        }
        response = self.client.post('/api/carts/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify cart item was created
        cart = Cart.objects.filter(user=self.user).first()
        self.assertEqual(cart.items.count(), 1)

    def test_add_duplicate_item_increases_quantity(self):
        """Test that adding duplicate item increases quantity"""
        data = {
            'variant_sku': self.variant.sku,
            'quantity': 2
        }
        self.client.post('/api/carts/', data)
        self.client.post('/api/carts/', data)
        
        cart = Cart.objects.filter(user=self.user).first()
        item = cart.items.first()
        self.assertEqual(item.quantity, 4)

    def test_get_cart(self):
        """Test retrieving cart"""
        # Create a cart first
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product_variant=self.variant, quantity=1)
        
        response = self.client.get('/api/carts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reduce_item_quantity(self):
        """Test reducing item quantity"""
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product_variant=self.variant, quantity=5)
        
        data = {
            'variant_sku': self.variant.sku,
            'quantity': 2
        }
        response = self.client.post('/api/carts/reduce_item/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        item = CartItem.objects.get(cart=cart, product_variant=self.variant)
        self.assertEqual(item.quantity, 3)

    def test_reduce_item_removes_when_quantity_zero(self):
        """Test that item is removed when quantity reaches zero"""
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product_variant=self.variant, quantity=2)
        
        data = {
            'variant_sku': self.variant.sku,
            'quantity': 2
        }
        response = self.client.post('/api/carts/reduce_item/', data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 0)

    def test_remove_item_from_cart(self):
        """Test removing an item completely from cart"""
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product_variant=self.variant, quantity=3)
        
        data = {'variant_sku': self.variant.sku}
        response = self.client.delete('/api/carts/remove_item/', data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 0)

    def test_remove_nonexistent_item(self):
        """Test removing a non-existent item from cart"""
        Cart.objects.create(user=self.user)
        
        data = {'variant_sku': 'nonexistent-sku'}
        response = self.client.delete('/api/carts/remove_item/', data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cart_unauthenticated(self):
        """Test accessing cart without authentication"""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/carts/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_destroy_cart_not_allowed(self):
        """Test that deleting cart is not allowed"""
        cart = Cart.objects.create(user=self.user)
        response = self.client.delete(f'/api/carts/{cart.id}/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class CartSignalTests(TestCase):
    """Test that cart signal creates cart for new users"""

    def test_cart_created_on_user_creation(self):
        """Test that a cart is automatically created when a user is created"""
        user = User.objects.create_user(
            email='newuser@example.com',
            password='testpass123',
            first_name='New',
            last_name='User'
        )
        cart = Cart.objects.filter(user=user).first()
        self.assertIsNotNone(cart)
        self.assertEqual(cart.user, user)
