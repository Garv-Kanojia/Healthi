from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch

from authentication.models import User
from authentication.utils import generate_otp


class RegistrationAPITest(APITestCase):
    """Test cases for user registration endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.url = reverse('authentication:register')
        self.valid_data = {
            'email': 'newuser@example.com',
            'password': 'TestPass123',
            'password_confirm': 'TestPass123',
            'name': 'New User',
            'age': 25,
            'gender': 'Male'
        }
    
    def test_register_with_valid_data(self):
        """Test successful registration with valid data"""
        response = self.client.post(self.url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], self.valid_data['email'])
        
        # Check user was created in database
        user = User.objects.get(email=self.valid_data['email'])
        self.assertIsNotNone(user)
        self.assertFalse(user.is_email_verified)
        self.assertIsNotNone(user.email_verification_otp)
    
    def test_register_without_email(self):
        """Test registration fails without email"""
        data = self.valid_data.copy()
        del data['email']
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_register_without_password(self):
        """Test registration fails without password"""
        data = self.valid_data.copy()
        del data['password']
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_register_with_mismatched_passwords(self):
        """Test registration fails when passwords don't match"""
        data = self.valid_data.copy()
        data['password_confirm'] = 'DifferentPass123'
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_register_with_duplicate_verified_email(self):
        """Test registration fails for already verified email"""
        # Create verified user
        User.objects.create_user(
            email=self.valid_data['email'],
            password='OldPass123',
            name='Old User',
            is_email_verified=True
        )
        
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('error', response.data)
        self.assertTrue(response.data['email_verified'])
    
    def test_register_with_duplicate_unverified_email(self):
        """Test registration fails for already registered but unverified email"""
        # Create unverified user
        User.objects.create_user(
            email=self.valid_data['email'],
            password='OldPass123',
            name='Old User',
            is_email_verified=False
        )
        
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('error', response.data)
        self.assertFalse(response.data['email_verified'])
    
    def test_register_with_invalid_email_format(self):
        """Test registration fails with invalid email format"""
        data = self.valid_data.copy()
        data['email'] = 'invalid-email'
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_register_with_weak_password(self):
        """Test registration fails with weak password"""
        data = self.valid_data.copy()
        data['password'] = 'weak'
        data['password_confirm'] = 'weak'
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_register_without_name(self):
        """Test registration fails without name"""
        data = self.valid_data.copy()
        del data['name']
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_register_with_optional_fields(self):
        """Test registration succeeds without optional fields"""
        data = {
            'email': 'minimal@example.com',
            'password': 'TestPass123',
            'password_confirm': 'TestPass123',
            'name': 'Minimal User'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class EmailVerificationAPITest(APITestCase):
    """Test cases for email verification endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.url = reverse('authentication:verify_email')
        self.user = User.objects.create_user(
            email='verify@example.com',
            password='TestPass123',
            name='Verify User',
            is_email_verified=False
        )
        self.otp = generate_otp()
        self.user.email_verification_otp = self.otp
        self.user.email_verification_sent_at = timezone.now()
        self.user.save()
    
    def test_verify_email_with_valid_otp(self):
        """Test successful email verification with valid OTP"""
        data = {
            'email': self.user.email,
            'otp': self.otp
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Check user is verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)
        self.assertIsNone(self.user.email_verification_otp)
    
    def test_verify_email_with_invalid_otp(self):
        """Test email verification fails with invalid OTP"""
        data = {
            'email': self.user.email,
            'otp': '000000'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
        # User should still be unverified
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)
    
    def test_verify_email_with_expired_otp(self):
        """Test email verification fails with expired OTP"""
        # Set OTP sent time to 2 hours ago
        self.user.email_verification_sent_at = timezone.now() - timedelta(hours=2)
        self.user.save()
        
        data = {
            'email': self.user.email,
            'otp': self.otp
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_verify_email_for_nonexistent_user(self):
        """Test email verification fails for non-existent user"""
        data = {
            'email': 'nonexistent@example.com',
            'otp': '123456'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_verify_already_verified_email(self):
        """Test verification fails for already verified email"""
        self.user.is_email_verified = True
        self.user.save()
        
        data = {
            'email': self.user.email,
            'otp': self.otp
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_verify_email_increments_attempts(self):
        """Test that failed verification increments attempt counter"""
        initial_attempts = self.user.email_verification_attempts
        
        data = {
            'email': self.user.email,
            'otp': '000000'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.user.refresh_from_db()
        self.assertGreater(self.user.email_verification_attempts, initial_attempts)
    
    def test_verify_email_without_email_field(self):
        """Test verification fails without email field"""
        data = {'otp': self.otp}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_verify_email_without_otp_field(self):
        """Test verification fails without OTP field"""
        data = {'email': self.user.email}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginAPITest(APITestCase):
    """Test cases for login endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.url = reverse('authentication:login')
        self.verified_user = User.objects.create_user(
            email='verified@example.com',
            password='TestPass123',
            name='Verified User',
            is_email_verified=True
        )
        self.unverified_user = User.objects.create_user(
            email='unverified@example.com',
            password='TestPass123',
            name='Unverified User',
            is_email_verified=False
        )
    
    def test_login_with_valid_credentials(self):
        """Test successful login with valid credentials"""
        data = {
            'email': self.verified_user.email,
            'password': 'TestPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_login_with_invalid_credentials(self):
        """Test login fails with invalid credentials"""
        data = {
            'email': self.verified_user.email,
            'password': 'WrongPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_login_with_unverified_email(self):
        """Test login fails for unverified email"""
        data = {
            'email': self.unverified_user.email,
            'password': 'TestPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertFalse(response.data['email_verified'])
        self.assertTrue(response.data['otp_sent'])
    
    def test_login_with_nonexistent_email(self):
        """Test login fails with non-existent email"""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'TestPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_without_email(self):
        """Test login fails without email"""
        data = {'password': 'TestPass123'}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_without_password(self):
        """Test login fails without password"""
        data = {'email': self.verified_user.email}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_returns_jwt_tokens(self):
        """Test that login returns valid JWT tokens"""
        data = {
            'email': self.verified_user.email,
            'password': 'TestPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check tokens are strings
        self.assertIsInstance(response.data['access'], str)
        self.assertIsInstance(response.data['refresh'], str)
        self.assertGreater(len(response.data['access']), 0)
        self.assertGreater(len(response.data['refresh']), 0)


class LogoutAPITest(APITestCase):
    """Test cases for logout endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.url = reverse('authentication:logout')
        self.user = User.objects.create_user(
            email='logout@example.com',
            password='TestPass123',
            name='Logout User',
            is_email_verified=True
        )
        self.client.force_authenticate(user=self.user)
    
    def test_logout_authenticated_user(self):
        """Test successful logout for authenticated user"""
        # Get refresh token
        refresh = RefreshToken.for_user(self.user)
        data = {'refresh': str(refresh)}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
    
    def test_logout_unauthenticated_user(self):
        """Test logout fails for unauthenticated user"""
        self.client.force_authenticate(user=None)
        
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PasswordResetRequestAPITest(APITestCase):
    """Test cases for password reset request endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.url = reverse('authentication:password_reset_request')
        self.verified_user = User.objects.create_user(
            email='resetpw@example.com',
            password='OldPass123',
            name='Reset User',
            is_email_verified=True
        )
        self.unverified_user = User.objects.create_user(
            email='unverified@example.com',
            password='OldPass123',
            name='Unverified User',
            is_email_verified=False
        )
    
    def test_password_reset_request_for_verified_user(self):
        """Test successful password reset request for verified user"""
        data = {'email': self.verified_user.email}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Check OTP was set
        self.verified_user.refresh_from_db()
        self.assertIsNotNone(self.verified_user.password_reset_otp)
        self.assertIsNotNone(self.verified_user.password_reset_sent_at)
    
    def test_password_reset_request_for_unverified_user(self):
        """Test password reset redirects to verification for unverified user"""
        data = {'email': self.unverified_user.email}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertFalse(response.data['email_verified'])
    
    def test_password_reset_request_for_nonexistent_user(self):
        """Test password reset doesn't reveal if user doesn't exist"""
        data = {'email': 'nonexistent@example.com'}
        
        response = self.client.post(self.url, data, format='json')
        # Should still return success to not reveal user existence
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
    
    def test_password_reset_request_without_email(self):
        """Test password reset fails without email"""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmAPITest(APITestCase):
    """Test cases for password reset confirm endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.url = reverse('authentication:password_reset_confirm')
        self.user = User.objects.create_user(
            email='confirm@example.com',
            password='OldPass123',
            name='Confirm User',
            is_email_verified=True
        )
        self.otp = generate_otp()
        self.user.password_reset_otp = self.otp
        self.user.password_reset_sent_at = timezone.now()
        self.user.save()
    
    def test_password_reset_confirm_with_valid_otp(self):
        """Test successful password reset with valid OTP"""
        data = {
            'email': self.user.email,
            'otp': self.otp,
            'password': 'NewPass123',
            'password_confirm': 'NewPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass123'))
        self.assertIsNone(self.user.password_reset_otp)
    
    def test_password_reset_confirm_with_invalid_otp(self):
        """Test password reset fails with invalid OTP"""
        data = {
            'email': self.user.email,
            'otp': '000000',
            'password': 'NewPass123',
            'password_confirm': 'NewPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Password should not be changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPass123'))
    
    def test_password_reset_confirm_with_expired_otp(self):
        """Test password reset fails with expired OTP"""
        self.user.password_reset_sent_at = timezone.now() - timedelta(hours=2)
        self.user.save()
        
        data = {
            'email': self.user.email,
            'otp': self.otp,
            'password': 'NewPass123',
            'password_confirm': 'NewPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_password_reset_confirm_with_mismatched_passwords(self):
        """Test password reset fails with mismatched passwords"""
        data = {
            'email': self.user.email,
            'otp': self.otp,
            'password': 'NewPass123',
            'password_confirm': 'DifferentPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_password_reset_confirm_for_nonexistent_user(self):
        """Test password reset fails for non-existent user"""
        data = {
            'email': 'nonexistent@example.com',
            'otp': '123456',
            'password': 'NewPass123',
            'password_confirm': 'NewPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_password_reset_confirm_increments_attempts(self):
        """Test that failed reset increments attempt counter"""
        initial_attempts = self.user.password_reset_attempts
        
        data = {
            'email': self.user.email,
            'otp': '000000',
            'password': 'NewPass123',
            'password_confirm': 'NewPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.user.refresh_from_db()
        self.assertGreater(self.user.password_reset_attempts, initial_attempts)


class ResendVerificationAPITest(APITestCase):
    """Test cases for resend verification endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.url = reverse('authentication:resend_verification')
        self.user = User.objects.create_user(
            email='resend@example.com',
            password='TestPass123',
            name='Resend User',
            is_email_verified=False
        )
    
    def test_resend_verification_for_unverified_user(self):
        """Test successful resend for unverified user"""
        data = {'email': self.user.email}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check new OTP was set
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.email_verification_otp)
        self.assertIsNotNone(self.user.email_verification_sent_at)
    
    def test_resend_verification_for_verified_user(self):
        """Test resend fails for already verified user"""
        self.user.is_email_verified = True
        self.user.save()
        
        data = {'email': self.user.email}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_resend_verification_for_nonexistent_user(self):
        """Test resend fails for non-existent user"""
        data = {'email': 'nonexistent@example.com'}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_resend_verification_rate_limiting(self):
        """Test rate limiting on resend verification"""
        # Set recent OTP sent time
        self.user.email_verification_sent_at = timezone.now() - timedelta(seconds=30)
        self.user.save()
        
        data = {'email': self.user.email}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
    
    def test_resend_verification_resets_attempts(self):
        """Test that resend resets attempt counter"""
        self.user.email_verification_attempts = 2
        self.user.save()
        
        data = {'email': self.user.email}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.email_verification_attempts, 0)


class UserProfileAPITest(APITestCase):
    """Test cases for user profile endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='profile@example.com',
            password='TestPass123',
            name='Profile User',
            age=30,
            gender='Male',
            is_email_verified=True
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('authentication:user_profile')
    
    def test_get_user_profile_authenticated(self):
        """Test getting user profile when authenticated"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertEqual(response.data['name'], self.user.name)
        self.assertEqual(response.data['age'], self.user.age)
    
    def test_get_user_profile_unauthenticated(self):
        """Test getting user profile fails when unauthenticated"""
        self.client.force_authenticate(user=None)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_user_profile_name(self):
        """Test updating user name"""
        data = {'name': 'Updated Name'}
        
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, 'Updated Name')
    
    def test_update_user_profile_age(self):
        """Test updating user age"""
        data = {'age': 35}
        
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.age, 35)
    
    def test_update_user_profile_gender(self):
        """Test updating user gender"""
        data = {'gender': 'Female'}
        
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.gender, 'Female')
    
    def test_update_user_profile_multiple_fields(self):
        """Test updating multiple fields at once"""
        data = {
            'name': 'New Name',
            'age': 40,
            'gender': 'Other'
        }
        
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, 'New Name')
        self.assertEqual(self.user.age, 40)
        self.assertEqual(self.user.gender, 'Other')
    
    def test_update_user_profile_invalid_age(self):
        """Test updating with invalid age fails"""
        data = {'age': 150}
        
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_update_user_profile_unauthenticated(self):
        """Test updating profile fails when unauthenticated"""
        self.client.force_authenticate(user=None)
        
        data = {'name': 'Hacker'}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ChangePasswordAPITest(APITestCase):
    """Test cases for change password endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.url = reverse('authentication:change_password')
        self.user = User.objects.create_user(
            email='changepw@example.com',
            password='OldPass123',
            name='Change Password User',
            is_email_verified=True
        )
        self.client.force_authenticate(user=self.user)
    
    def test_change_password_with_valid_data(self):
        """Test successful password change"""
        data = {
            'current_password': 'OldPass123',
            'new_password': 'NewPass123',
            'new_password_confirm': 'NewPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass123'))
        self.assertFalse(self.user.check_password('OldPass123'))
    
    def test_change_password_with_wrong_current_password(self):
        """Test password change fails with wrong current password"""
        data = {
            'current_password': 'WrongPass123',
            'new_password': 'NewPass123',
            'new_password_confirm': 'NewPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Password should not be changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPass123'))
    
    def test_change_password_with_mismatched_new_passwords(self):
        """Test password change fails with mismatched new passwords"""
        data = {
            'current_password': 'OldPass123',
            'new_password': 'NewPass123',
            'new_password_confirm': 'DifferentPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_change_password_with_weak_new_password(self):
        """Test password change fails with weak new password"""
        data = {
            'current_password': 'OldPass123',
            'new_password': 'weak',
            'new_password_confirm': 'weak'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_change_password_unauthenticated(self):
        """Test password change fails when unauthenticated"""
        self.client.force_authenticate(user=None)
        
        data = {
            'current_password': 'OldPass123',
            'new_password': 'NewPass123',
            'new_password_confirm': 'NewPass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MedicalNotesProfileAPITest(APITestCase):
    """Test cases for medical notes through user profile endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='medical@example.com',
            password='TestPass123',
            name='Medical User',
            is_email_verified=True
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('authentication:user_profile')
    
    def test_update_medical_notes(self):
        """Test updating medical notes through profile"""
        data = {'medical_notes': 'Diagnosed with EDS Type III in 2020'}
        
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('medical_notes', response.data)
        
        # Check medical notes were updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.medical_notes, data['medical_notes'])
    
    def test_get_medical_notes_in_profile(self):
        """Test getting medical notes in profile response"""
        self.user.medical_notes = 'Test medical notes'
        self.user.save()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['medical_notes'], 'Test medical notes')
    
    def test_update_medical_notes_with_empty_notes(self):
        """Test updating with empty medical notes"""
        self.user.medical_notes = 'Old notes'
        self.user.save()
        
        data = {'medical_notes': ''}
        
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.medical_notes, '')
    
    def test_has_medical_history_flag(self):
        """Test has_medical_history flag in profile response"""
        # Without medical notes
        response = self.client.get(self.url)
        self.assertFalse(response.data['has_medical_history'])
        
        # With medical notes
        self.user.medical_notes = 'Some notes'
        self.user.save()
        
        response = self.client.get(self.url)
        self.assertTrue(response.data['has_medical_history'])
    
    def test_medical_notes_unauthenticated(self):
        """Test medical notes update fails when unauthenticated"""
        self.client.force_authenticate(user=None)
        
        data = {'medical_notes': 'Test'}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class JWTTokenRefreshAPITest(APITestCase):
    """Test cases for JWT token refresh endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.url = reverse('authentication:token_refresh')
        self.user = User.objects.create_user(
            email='token@example.com',
            password='TestPass123',
            name='Token User',
            is_email_verified=True
        )
        self.refresh = RefreshToken.for_user(self.user)
    
    def test_refresh_token_with_valid_token(self):
        """Test token refresh with valid refresh token"""
        data = {'refresh': str(self.refresh)}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
    
    def test_refresh_token_with_invalid_token(self):
        """Test token refresh fails with invalid token"""
        data = {'refresh': 'invalid.token.here'}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_refresh_token_without_token(self):
        """Test token refresh fails without token"""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class APIIntegrationTest(APITestCase):
    """Integration tests for complete user flows"""
    
    def test_complete_registration_verification_login_flow(self):
        """Test complete flow: register -> verify -> login"""
        # Step 1: Register
        register_data = {
            'email': 'integration@example.com',
            'password': 'TestPass123',
            'password_confirm': 'TestPass123',
            'name': 'Integration User',
            'age': 28,
            'gender': 'Male'
        }
        
        register_response = self.client.post(
            reverse('authentication:register'),
            register_data,
            format='json'
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        
        # Get the user and OTP
        user = User.objects.get(email=register_data['email'])
        otp = user.email_verification_otp
        
        # Step 2: Verify email
        verify_data = {
            'email': user.email,
            'otp': otp
        }
        
        verify_response = self.client.post(
            reverse('authentication:verify_email'),
            verify_data,
            format='json'
        )
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        
        # Step 3: Login
        login_data = {
            'email': user.email,
            'password': register_data['password']
        }
        
        login_response = self.client.post(
            reverse('authentication:login'),
            login_data,
            format='json'
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.data)
        self.assertIn('refresh', login_response.data)
    
    def test_complete_password_reset_flow(self):
        """Test complete flow: request reset -> confirm reset -> login"""
        # Create verified user
        user = User.objects.create_user(
            email='resetflow@example.com',
            password='OldPass123',
            name='Reset Flow User',
            is_email_verified=True
        )
        
        # Step 1: Request password reset
        request_data = {'email': user.email}
        
        request_response = self.client.post(
            reverse('authentication:password_reset_request'),
            request_data,
            format='json'
        )
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)
        
        # Get OTP
        user.refresh_from_db()
        otp = user.password_reset_otp
        
        # Step 2: Confirm password reset
        confirm_data = {
            'email': user.email,
            'otp': otp,
            'password': 'NewPass123',
            'password_confirm': 'NewPass123'
        }
        
        confirm_response = self.client.post(
            reverse('authentication:password_reset_confirm'),
            confirm_data,
            format='json'
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        
        # Step 3: Login with new password
        login_data = {
            'email': user.email,
            'password': 'NewPass123'
        }
        
        login_response = self.client.post(
            reverse('authentication:login'),
            login_data,
            format='json'
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
    
    def test_authenticated_user_crud_operations(self):
        """Test authenticated user can perform CRUD on profile and medical history"""
        # Create and authenticate user
        user = User.objects.create_user(
            email='crud@example.com',
            password='TestPass123',
            name='CRUD User',
            is_email_verified=True
        )
        self.client.force_authenticate(user=user)
        
        # Get profile
        profile_response = self.client.get(reverse('authentication:user_profile'))
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        
        # Update profile
        update_data = {'name': 'Updated CRUD User', 'age': 30}
        update_response = self.client.patch(
            reverse('authentication:user_profile'),
            update_data,
            format='json'
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # Create medical history
        medical_data = {'medical_notes': 'Test medical history'}
        medical_response = self.client.post(
            reverse('authentication:medical_history'),
            medical_data,
            format='json'
        )
        self.assertEqual(medical_response.status_code, status.HTTP_201_CREATED)
        
        # Get medical history
        get_medical_response = self.client.get(reverse('authentication:medical_history'))
        self.assertEqual(get_medical_response.status_code, status.HTTP_200_OK)
        
        # Change password
        password_data = {
            'current_password': 'TestPass123',
            'new_password': 'NewTestPass123',
            'new_password_confirm': 'NewTestPass123'
        }
        password_response = self.client.post(
            reverse('authentication:change_password'),
            password_data,
            format='json'
        )
        self.assertEqual(password_response.status_code, status.HTTP_200_OK)
