from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator

class User(AbstractUser):
    """
    Custom User model using email as the unique identifier instead of username.
    Includes OTP fields for email verification and password reset.
    """
    
    # Gender choices
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Prefer not to say', 'Prefer not to say'),
        ('Other', 'Other'),
    ]
    
    # Override default username - use email as unique identifier
    username = None
    email = models.EmailField(unique=True, db_index=True)
    
    # Basic Information
    name = models.CharField(max_length=150)
    age = models.PositiveIntegerField(
        null=True, 
        blank=False,
        validators=[MinValueValidator(1), MaxValueValidator(120)]
    )
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=False)
    
    # Authentication Fields
    is_email_verified = models.BooleanField(default=False)
    email_verification_otp = models.CharField(max_length=6, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    email_verification_attempts = models.PositiveIntegerField(default=0)
    
    # Password Reset Fields
    password_reset_otp = models.CharField(max_length=6, blank=True, null=True)
    password_reset_sent_at = models.DateTimeField(null=True, blank=True)
    password_reset_attempts = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    # Settings
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email} - {self.name}"


class MedicalHistory(models.Model):
    """
    Medical history model for storing optional medical information.
    One-to-one relationship with User model.
    """
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='medical_history'
    )
    
    # Medical Information - Single optional text field
    medical_notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_history'
        verbose_name = 'Medical History'
        verbose_name_plural = 'Medical Histories'
    
    def __str__(self):
        return f"Medical History for {self.user.email}"
