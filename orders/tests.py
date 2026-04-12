from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Order, OrderItem
from address.models import Address
from carts.models import Cart, CartItem
from products.models import Product, ProductVariant
from unittest.mock import patch, MagicMock

User = get_user_model()


class OrderModelTests(TestCase):
    """Test Order model core functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_order_status_choices(self):
        """Test that order status is limited to valid choices"""
        order = Order.objects.create(
            user=self.user,
            shipping_address_snapshot='Address',
            total_price=50.00,
            status='confirmed'
        )
        self.assertEqual(order.status, 'confirmed')


class OrderItemModelTests(TestCase):
    """Test OrderItem model core functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.order = Order.objects.create(
            user=self.user,
            shipping_address_snapshot='Address',
            total_price=100.00
        )
        self.product = Product.objects.create(
            name='Test Product',
            description='Test'
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name='Standard',
            price=50.00,
            stock_quantity=100
        )

    def test_order_item_relationship(self):
        """Test that deleting order deletes items"""
        item = OrderItem.objects.create(
            order=self.order,
            quantity=1,
            variant_snapshot={'sku': self.variant.sku}
        )
        self.order.delete()
        self.assertFalse(OrderItem.objects.filter(id=item.id).exists())


class CheckoutViewTests(APITestCase):
    """Test Checkout view"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create product and variant
        self.product = Product.objects.create(
            name='Test Product',
            description='Test'
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name='Standard',
            price=50.00,
            stock_quantity=100
        )
        
        # Create address
        self.address = Address.objects.create(
            user=self.user,
            label='Home',
            country='USA',
            state='CA',
            city='Los Angeles',
            street='123 Main St',
            phone_number='1234567890',
            is_default=True
        )
        
        # Create cart with items
        self.cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=self.cart,
            product_variant=self.variant,
            quantity=2
        )

    def test_checkout_success(self):
        """Test successful checkout"""
        with patch('orders.services.PaystackService.initialize_paystack_payment') as mock_paystack:
            mock_paystack.return_value = {
                'status': True,
                'data': {'authorization_url': 'https://checkout.paystack.com/test'}
            }
            
            response = self.client.post('/api/orders/checkout/')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn('checkout_url', response.data)
            self.assertIn('tx_ref', response.data)

    def test_checkout_empty_cart(self):
        """Test checkout with empty cart"""
        self.cart.items.all().delete()
        response = self.client.post('/api/orders/checkout/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_no_default_address(self):
        """Test checkout without default address"""
        self.address.is_default = False
        self.address.save()
        
        response = self.client.post('/api/orders/checkout/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('address', response.data['error'].lower())

    def test_checkout_out_of_stock(self):
        """Test checkout with out of stock item"""
        self.variant.stock_quantity = 1
        self.variant.save()
        
        response = self.client.post('/api/orders/checkout/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('stock', response.data['error'].lower())

    def test_checkout_unauthenticated(self):
        """Test checkout without authentication"""
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/orders/checkout/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_checkout_creates_order_and_items(self):
        """Test that checkout creates order and order items"""
        with patch('orders.services.PaystackService.initialize_paystack_payment') as mock_paystack:
            mock_paystack.return_value = {
                'status': True,
                'data': {'authorization_url': 'https://checkout.paystack.com/test'}
            }
            
            self.client.post('/api/orders/checkout/')
            
            order = Order.objects.filter(user=self.user).first()
            self.assertIsNotNone(order)
            self.assertEqual(order.items.count(), 1)
            self.assertEqual(order.status, 'pending')


class OrderViewSetTests(APITestCase):
    """Test Order ViewSet"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            first_name='Other',
            last_name='User'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create orders
        self.order = Order.objects.create(
            user=self.user,
            shipping_address_snapshot='Address',
            total_price=100.00,
            status='confirmed'
        )
        self.other_order = Order.objects.create(
            user=self.other_user,
            shipping_address_snapshot='Address',
            total_price=50.00,
            status='confirmed'
        )

    def test_get_user_orders(self):
        """Test getting user's orders"""
        response = self.client.get('/api/orders/my-orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.order.id)

    def test_get_orders_not_show_other_users_orders(self):
        """Test that users can't see other users' orders"""
        response = self.client.get('/api/orders/my-orders/')
        order_ids = [order['id'] for order in response.data]
        self.assertNotIn(self.other_order.id, order_ids)

    def test_get_orders_unauthenticated(self):
        """Test getting orders without authentication"""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/orders/my-orders/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class VerifyPaymentViewTests(APITestCase):
    """Test Payment Verification view"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.order = Order.objects.create(
            user=self.user,
            shipping_address_snapshot='Address',
            total_price=100.00,
            status='pending'
        )

    def test_verify_payment_success(self):
        """Test successful payment verification"""
        with patch('orders.services.PaystackService.verify_payment') as mock_verify:
            with patch('orders.tasks.process_order_payment.delay') as mock_task:
                mock_verify.return_value = {
                    'status': True,
                    'data': {'status': 'success'}
                }
                
                response = self.client.get(f'/api/orders/verify-payment/{self.order.tx_ref}')
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn('verified', response.data['message'].lower())
                mock_task.assert_called_once()

    def test_verify_payment_failed(self):
        """Test failed payment verification"""
        with patch('orders.services.PaystackService.verify_payment') as mock_verify:
            mock_verify.return_value = {
                'status': True,
                'data': {'status': 'failed'}
            }
            
            response = self.client.get(f'/api/orders/verify-payment/{self.order.tx_ref}')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_payment_nonexistent_order(self):
        """Test verifying payment for non-existent order"""
        response = self.client.get('/api/orders/verify-payment/nonexistent-ref')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
