from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from authentication.models import User
import time


class UserModelTest(TestCase):
    """Test cases for the User model"""
    
    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'email': 'test@example.com',
            'password': 'TestPass123',
            'name': 'Test User',
            'age': 30,
            'gender': 'Male'
        }
    
    def test_create_user_with_email(self):
        """Test creating a user with email (no username)"""
        user = User.objects.create_user(
            email=self.user_data['email'],
            password=self.user_data['password'],
            name=self.user_data['name']
        )
        
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.name, self.user_data['name'])
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertFalse(user.is_email_verified)
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
    
    def test_create_user_with_all_fields(self):
        """Test creating a user with all optional fields"""
        user = User.objects.create_user(
            email=self.user_data['email'],
            password=self.user_data['password'],
            name=self.user_data['name'],
            age=self.user_data['age'],
            gender=self.user_data['gender']
        )
        
        self.assertEqual(user.age, 30)
        self.assertEqual(user.gender, 'Male')
    
    def test_user_email_unique(self):
        """Test that email must be unique"""
        User.objects.create_user(
            email=self.user_data['email'],
            password=self.user_data['password'],
            name=self.user_data['name']
        )
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email=self.user_data['email'],
                password='DifferentPass123',
                name='Different User'
            )
    
    def test_user_string_representation(self):
        """Test the __str__ method of User model"""
        user = User.objects.create_user(
            email=self.user_data['email'],
            password=self.user_data['password'],
            name=self.user_data['name']
        )
        
        expected_str = f"{self.user_data['email']} - {self.user_data['name']}"
        self.assertEqual(str(user), expected_str)
    
    def test_user_email_verification_defaults(self):
        """Test default values for email verification fields"""
        user = User.objects.create_user(
            email=self.user_data['email'],
            password=self.user_data['password'],
            name=self.user_data['name']
        )
        
        self.assertFalse(user.is_email_verified)
        self.assertIsNone(user.email_verification_otp)
        self.assertIsNone(user.email_verification_sent_at)
        self.assertEqual(user.email_verification_attempts, 0)
    
    def test_user_password_reset_defaults(self):
        """Test default values for password reset fields"""
        user = User.objects.create_user(
            email=self.user_data['email'],
            password=self.user_data['password'],
            name=self.user_data['name']
        )
        
        self.assertIsNone(user.password_reset_otp)
        self.assertIsNone(user.password_reset_sent_at)
        self.assertEqual(user.password_reset_attempts, 0)
    
    def test_user_otp_fields_can_be_set(self):
        """Test that OTP fields can be set and updated"""
        user = User.objects.create_user(
            email=self.user_data['email'],
            password=self.user_data['password'],
            name=self.user_data['name']
        )
        
        # Set email verification OTP
        user.email_verification_otp = '123456'
        user.email_verification_sent_at = timezone.now()
        user.email_verification_attempts = 1
        user.save()
        
        user.refresh_from_db()
        self.assertEqual(user.email_verification_otp, '123456')
        self.assertIsNotNone(user.email_verification_sent_at)
        self.assertEqual(user.email_verification_attempts, 1)
        
        # Set password reset OTP
        user.password_reset_otp = '654321'
        user.password_reset_sent_at = timezone.now()
        user.password_reset_attempts = 2
        user.save()
        
        user.refresh_from_db()
        self.assertEqual(user.password_reset_otp, '654321')
        self.assertIsNotNone(user.password_reset_sent_at)
        self.assertEqual(user.password_reset_attempts, 2)
    
    def test_user_age_validation(self):
        """Test age field validation (1-120)"""
        user = User.objects.create_user(
            email=self.user_data['email'],
            password=self.user_data['password'],
            name=self.user_data['name'],
            age=25,
            gender='Male'
        )
        user.full_clean()  # Should not raise
        
        # Test invalid age (0)
        user.age = 0
        with self.assertRaises(ValidationError):
            user.full_clean()
        
        # Test invalid age (121)
        user.age = 121
        with self.assertRaises(ValidationError):
            user.full_clean()
        
        # Test valid boundary values
        user.age = 1
        user.full_clean()  # Should not raise
        
        user.age = 120
        user.full_clean()  # Should not raise
    
    def test_user_gender_choices(self):
        """Test gender field with valid choices"""
        valid_genders = ['Male', 'Female', 'Prefer not to say', 'Other']
        
        for gender in valid_genders:
            user = User.objects.create_user(
                email=f'test_{gender}@example.com',
                password=self.user_data['password'],
                name=self.user_data['name'],
                gender=gender
            )
            self.assertEqual(user.gender, gender)
    
    def test_user_timestamps_auto_update(self):
        """Test that timestamps are automatically managed"""
        user = User.objects.create_user(
            email=self.user_data['email'],
            password=self.user_data['password'],
            name=self.user_data['name']
        )
        
        created_at = user.created_at
        updated_at = user.updated_at
        
        # Ensure some time passes
        time.sleep(0.1)

        # Update user
        user.name = 'Updated Name'
        user.save()
        user.refresh_from_db()
        
        # created_at should remain the same
        self.assertEqual(user.created_at, created_at)
        # updated_at should be newer
        self.assertGreater(user.updated_at, updated_at)
    
    def test_user_email_as_username_field(self):
        """Test that email is used as USERNAME_FIELD"""
        self.assertEqual(User.USERNAME_FIELD, 'email')
    
    def test_user_required_fields(self):
        """Test REQUIRED_FIELDS configuration"""
        self.assertIn('name', User.REQUIRED_FIELDS)
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123',
            name='Admin User'
        )
        
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertEqual(superuser.email, 'admin@example.com')


class UserMedicalNotesTest(TestCase):
    """Test cases for medical_notes field on User model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='medical@example.com',
            password='TestPass123',
            name='Medical Test User'
        )
    
    def test_create_user_with_medical_notes(self):
        """Test creating a user with medical notes"""
        user = User.objects.create_user(
            email='test_medical@example.com',
            password='TestPass123',
            name='Test User',
            medical_notes='Diagnosed with EDS Type III'
        )
        
        self.assertEqual(user.medical_notes, 'Diagnosed with EDS Type III')
    
    def test_medical_notes_default_empty(self):
        """Test that medical_notes defaults to empty string"""
        self.assertEqual(self.user.medical_notes, '')
    
    def test_medical_notes_can_be_blank(self):
        """Test that medical_notes can be blank"""
        self.user.medical_notes = ''
        self.user.full_clean()  # Should not raise ValidationError
    
    def test_medical_notes_update(self):
        """Test updating medical notes"""
        self.user.medical_notes = 'Initial notes'
        self.user.save()
        
        updated_at = self.user.updated_at
        
        # Ensure some time passes
        time.sleep(0.1)

        # Update notes
        self.user.medical_notes = 'Updated notes with more information'
        self.user.save()
        self.user.refresh_from_db()
        
        self.assertEqual(self.user.medical_notes, 'Updated notes with more information')
        # updated_at should be newer
        self.assertGreater(self.user.updated_at, updated_at)
    
    def test_medical_notes_deleted_with_user(self):
        """Test that medical notes are deleted when user is deleted"""
        self.user.medical_notes = 'Test notes'
        self.user.save()
        
        user_id = self.user.id
        
        # Delete the user
        self.user.delete()
        
        # User (and their medical notes) should be deleted
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=user_id)

