from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from .models import User, MedicalHistory


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'name', 'age', 'gender']
        extra_kwargs = {
            'age': {'required': False},
            'gender': {'required': False},
        }
    
    def validate(self, attrs):
        """Validate passwords match"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        return attrs
    
    def create(self, validated_data):
        """Create user with hashed password"""
        validated_data.pop('password_confirm')
        
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data['name'],
            age=validated_data.get('age'),
            gender=validated_data.get('gender', ''),
            is_email_verified=False
        )
        
        return user


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification"""
    
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, max_length=6, min_length=6)


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class TokenRefreshSerializer(serializers.Serializer):
    """Serializer for token refresh"""
    
    refresh = serializers.CharField(required=True)


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout"""
    
    refresh = serializers.CharField(required=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, max_length=6, min_length=6)
    password = serializers.CharField(
        required=True, 
        write_only=True, 
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        """Validate passwords match"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        return attrs


class ResendVerificationSerializer(serializers.Serializer):
    """Serializer for resending verification OTP"""
    
    email = serializers.EmailField(required=True)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    has_medical_history = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'age', 'gender', 
            'is_email_verified', 'created_at', 'has_medical_history'
        ]
        read_only_fields = ['id', 'email', 'is_email_verified', 'created_at']
    
    def get_has_medical_history(self, obj):
        """Check if user has medical history"""
        return hasattr(obj, 'medical_history')


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = ['name', 'age', 'gender']
        extra_kwargs = {
            'name': {'required': False},
            'age': {'required': False},
            'gender': {'required': False},
        }


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password (authenticated)"""
    
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True, 
        write_only=True, 
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        """Validate passwords match"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Passwords do not match.'
            })
        return attrs


class MedicalHistorySerializer(serializers.ModelSerializer):
    """Serializer for medical history"""
    
    class Meta:
        model = MedicalHistory
        fields = ['id', 'medical_notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserResponseSerializer(serializers.ModelSerializer):
    """Serializer for user response in authentication"""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'age', 'gender', 
            'is_email_verified', 'created_at'
        ]
