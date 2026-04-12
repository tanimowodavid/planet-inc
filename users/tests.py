from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserModelTests(TestCase):
    """Test User model core functionality"""

    def test_create_superuser(self):
        """Test creating a superuser"""
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_email_is_unique(self):
        """Test that email field is unique"""
        User.objects.create_user(
            email='duplicate@example.com',
            password='pass123',
            first_name='First',
            last_name='User'
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
                email='duplicate@example.com',
                password='pass123',
                first_name='Second',
                last_name='User'
            )

    def test_email_is_required(self):
        """Test that email field is required"""
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email='',
                password='pass123',
                first_name='Test',
                last_name='User'
            )


class UserRegistrationTests(APITestCase):
    """Test user registration endpoint"""

    def test_register_user_success(self):
        """Test successful user registration"""
        data = {
            'email': 'newuser@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'securepass123',
            'password2': 'securepass123'
        }
        response = self.client.post('/api/users/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'newuser@example.com')
        self.assertIn('id', response.data)

    def test_register_user_password_mismatch(self):
        """Test registration with mismatched passwords"""
        data = {
            'email': 'newuser@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'securepass123',
            'password2': 'differentpass123'
        }
        response = self.client.post('/api/users/register/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_user_missing_required_field(self):
        """Test registration with missing required field"""
        data = {
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'password2': 'securepass123'
        }
        response = self.client.post('/api/users/register/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        """Test registration with duplicate email"""
        User.objects.create_user(
            email='existing@example.com',
            password='pass123',
            first_name='Existing',
            last_name='User'
        )
        data = {
            'email': 'existing@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'securepass123',
            'password2': 'securepass123'
        }
        response = self.client.post('/api/users/register/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLoginTests(APITestCase):
    """Test user login functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_login_success(self):
        """Test successful login"""
        data = {
            'email': 'testuser@example.com',
            'password': 'testpass123'
        }
        response = self.client.post('/api/users/login/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_invalid_email(self):
        """Test login with non-existent email"""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'testpass123'
        }
        response = self.client.post('/api/users/login/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_wrong_password(self):
        """Test login with wrong password"""
        data = {
            'email': 'testuser@example.com',
            'password': 'wrongpass123'
        }
        response = self.client.post('/api/users/login/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        """Test refreshing access token"""
        # First login
        login_data = {
            'email': 'testuser@example.com',
            'password': 'testpass123'
        }
        login_response = self.client.post('/api/users/login/', login_data)
        refresh_token = login_response.data['refresh']

        # Refresh token
        refresh_data = {'refresh': refresh_token}
        response = self.client.post('/api/users/refresh/', refresh_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


class UserProfileTests(APITestCase):
    """Test user profile endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_profile(self):
        """Test retrieving user profile"""
        response = self.client.get('/api/users/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'testuser@example.com')
        self.assertEqual(response.data['first_name'], 'Test')

    def test_update_profile(self):
        """Test updating user profile"""
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'newemail@example.com'
        }
        response = self.client.put('/api/users/profile/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.email, 'newemail@example.com')

    def test_partial_update_profile(self):
        """Test partial update of user profile"""
        data = {
            'first_name': 'PartialUpdate'
        }
        response = self.client.patch('/api/users/profile/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'PartialUpdate')
        self.assertEqual(self.user.last_name, 'User')  # Should remain unchanged

    def test_profile_unauthenticated(self):
        """Test accessing profile without authentication"""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/users/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ChangePasswordTests(APITestCase):
    """Test password change functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='oldpass123',
            first_name='Test',
            last_name='User'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_change_password_success(self):
        """Test successful password change"""
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123'
        }
        response = self.client.post('/api/users/change-password/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))

    def test_change_password_wrong_old_password(self):
        """Test password change with wrong old password"""
        data = {
            'old_password': 'wrongoldpass',
            'new_password': 'newpass123'
        }
        response = self.client.post('/api/users/change-password/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_unauthenticated(self):
        """Test password change without authentication"""
        self.client.force_authenticate(user=None)
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123'
        }
        response = self.client.post('/api/users/change-password/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutTests(APITestCase):
    """Test logout functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.client = APIClient()
        # Login and get tokens
        login_response = self.client.post('/api/users/login/', {
            'email': 'testuser@example.com',
            'password': 'testpass123'
        })
        self.refresh_token = login_response.data['refresh']
        self.client.force_authenticate(user=self.user)

    def test_logout_success(self):
        """Test successful logout"""
        data = {'refresh': self.refresh_token}
        response = self.client.post('/api/users/logout/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_unauthenticated(self):
        """Test logout without authentication"""
        self.client.force_authenticate(user=None)
        data = {'refresh': self.refresh_token}
        response = self.client.post('/api/users/logout/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_invalid_token(self):
        """Test logout with invalid refresh token"""
        data = {'refresh': 'invalid_token'}
        response = self.client.post('/api/users/logout/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
