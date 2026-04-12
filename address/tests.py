from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Address

User = get_user_model()


class AddressModelTests(TestCase):
    """Test Address model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_first_address_is_default(self):
        """Test that first address is set as default"""
        address = Address.objects.create(
            user=self.user,
            label='Home',
            country='USA',
            state='CA',
            city='Los Angeles',
            street='123 Main St',
            phone_number='1234567890'
        )
        self.assertTrue(address.is_default)

    def test_only_one_default_address(self):
        """Test that only one address can be default"""
        address1 = Address.objects.create(
            user=self.user,
            label='Home',
            country='USA',
            state='CA',
            city='Los Angeles',
            street='123 Main St',
            phone_number='1234567890',
            is_default=True
        )
        address2 = Address.objects.create(
            user=self.user,
            label='Work',
            country='USA',
            state='CA',
            city='San Francisco',
            street='456 Work Ave',
            phone_number='0987654321',
            is_default=True
        )
        
        address1.refresh_from_db()
        self.assertFalse(address1.is_default)
        self.assertTrue(address2.is_default)

    def test_cannot_unset_only_default(self):
        """Test that if only one address exists, it must remain default"""
        address = Address.objects.create(
            user=self.user,
            label='Home',
            country='USA',
            state='CA',
            city='Los Angeles',
            street='123 Main St',
            phone_number='1234567890'
        )
        address.is_default = False
        address.save()
        
        address.refresh_from_db()
        self.assertTrue(address.is_default)

    def test_address_multiple_users(self):
        """Test that addresses are isolated per user"""
        user2 = User.objects.create_user(
            email='testuser2@example.com',
            password='testpass123',
            first_name='Test2',
            last_name='User2'
        )
        addr1 = Address.objects.create(
            user=self.user,
            label='Home',
            country='USA',
            state='CA',
            city='Los Angeles',
            street='123 Main St',
            phone_number='1234567890'
        )
        addr2 = Address.objects.create(
            user=user2,
            label='Home',
            country='USA',
            state='NY',
            city='New York',
            street='456 Park Ave',
            phone_number='5555555555'
        )
        
        user1_addresses = Address.objects.filter(user=self.user)
        user2_addresses = Address.objects.filter(user=user2)
        
        self.assertEqual(user1_addresses.count(), 1)
        self.assertEqual(user2_addresses.count(), 1)
        self.assertIn(addr1, user1_addresses)
        self.assertIn(addr2, user2_addresses)


class AddressAPITests(APITestCase):
    """Test Address API endpoints"""

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

    def test_create_address(self):
        """Test creating an address"""
        data = {
            'label': 'Home',
            'country': 'USA',
            'state': 'CA',
            'city': 'Los Angeles',
            'street': '123 Main St',
            'phone_number': '1234567890'
        }
        response = self.client.post('/api/addresses/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['label'], 'Home')

    def test_create_address_unauthenticated(self):
        """Test creating address without authentication"""
        self.client.force_authenticate(user=None)
        data = {
            'label': 'Home',
            'country': 'USA',
            'state': 'CA',
            'city': 'Los Angeles',
            'street': '123 Main St',
            'phone_number': '1234567890'
        }
        response = self.client.post('/api/addresses/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_own_addresses(self):
        """Test listing user's own addresses"""
        addr = Address.objects.create(
            user=self.user,
            label='Home',
            country='USA',
            state='CA',
            city='Los Angeles',
            street='123 Main St',
            phone_number='1234567890'
        )
        
        response = self.client.get('/api/addresses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], addr.id)

    def test_list_addresses_only_own(self):
        """Test that users only see their own addresses"""
        addr1 = Address.objects.create(
            user=self.user,
            label='Home',
            country='USA',
            state='CA',
            city='Los Angeles',
            street='123 Main St',
            phone_number='1234567890'
        )
        addr2 = Address.objects.create(
            user=self.other_user,
            label='Work',
            country='USA',
            state='NY',
            city='New York',
            street='456 Park Ave',
            phone_number='5555555555'
        )
        
        response = self.client.get('/api/addresses/')
        address_ids = [addr['id'] for addr in response.data]
        self.assertIn(addr1.id, address_ids)
        self.assertNotIn(addr2.id, address_ids)

    def test_retrieve_address(self):
        """Test retrieving a specific address"""
        address = Address.objects.create(
            user=self.user,
            label='Home',
            country='USA',
            state='CA',
            city='Los Angeles',
            street='123 Main St',
            phone_number='1234567890'
        )
        
        response = self.client.get(f'/api/addresses/{address.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['label'], 'Home')

    def test_retrieve_other_users_address_fails(self):
        """Test that users can't retrieve other users' addresses"""
        address = Address.objects.create(
            user=self.other_user,
            label='Home',
            country='USA',
            state='NY',
            city='New York',
            street='456 Park Ave',
            phone_number='5555555555'
        )
        
        response = self.client.get(f'/api/addresses/{address.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_address(self):
        """Test updating an address"""
        address = Address.objects.create(
            user=self.user,
            label='Home',
            country='USA',
            state='CA',
            city='Los Angeles',
            street='123 Main St',
            phone_number='1234567890'
        )
        
        data = {
            'label': 'Updated Home',
            'city': 'San Diego'
        }
        response = self.client.patch(f'/api/addresses/{address.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        address.refresh_from_db()
        self.assertEqual(address.label, 'Updated Home')

    def test_delete_address(self):
        """Test deleting an address"""
        address = Address.objects.create(
            user=self.user,
            label='Home',
            country='USA',
            state='CA',
            city='Los Angeles',
            street='123 Main St',
            phone_number='1234567890'
        )
        
        response = self.client.delete(f'/api/addresses/{address.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Address.objects.filter(id=address.id).exists())

    def test_set_default_address(self):
        """Test setting an address as default"""
        addr1 = Address.objects.create(
            user=self.user,
            label='Home',
            country='USA',
            state='CA',
            city='Los Angeles',
            street='123 Main St',
            phone_number='1234567890',
            is_default=True
        )
        addr2 = Address.objects.create(
            user=self.user,
            label='Work',
            country='USA',
            state='CA',
            city='San Francisco',
            street='456 Work Ave',
            phone_number='0987654321',
            is_default=False
        )
        
        data = {'is_default': True}
        response = self.client.patch(f'/api/addresses/{addr2.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        addr1.refresh_from_db()
        addr2.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)
