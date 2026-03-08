from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db import transaction

from .models import User
from .serializers import (
    UserRegistrationSerializer,
    EmailVerificationSerializer,
    UserLoginSerializer,
    LogoutSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    ResendVerificationSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    ChangePasswordSerializer,

    UserResponseSerializer,
)
from .utils import (
    generate_otp,
    is_otp_expired,
    can_resend_otp,
    validate_otp,
    clear_otp,
    increment_otp_attempts,
)
from .emails import send_verification_email, send_password_reset_email


# ========== AUTHENTICATION ENDPOINTS ==========

@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def register(request):
    """
    Register a new user account.
    Endpoint: POST /api/auth/register/
    """
    # Check if email already exists BEFORE validation
    email = request.data.get('email')
    if email:
        existing_user = User.objects.filter(email=email).first()
        
        if existing_user:
            if existing_user.is_email_verified:
                # Email exists and is verified
                return Response({
                    'error': 'This email is already registered and verified.',
                    'message': 'Please login with your credentials or use password reset if you forgot your password.',
                    'action': 'redirect_to_login',
                    'email_verified': True
                }, status=status.HTTP_409_CONFLICT)
            else:
                # Email exists but not verified
                return Response({
                    'error': 'This email is already registered but not verified.',
                    'message': 'Please go to the login page and attempt to login. You will be prompted to verify your email.',
                    'action': 'redirect_to_login',
                    'email_verified': False
                }, status=status.HTTP_409_CONFLICT)
    
    # Now validate the serializer
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        # Create new user
        user = serializer.save()
        
        # Generate and send OTP
        otp = generate_otp()
        user.email_verification_otp = otp
        user.email_verification_sent_at = timezone.now()
        user.save()
        
        # Send verification email
        send_verification_email(user, otp)
        
        # Prepare response
        user_data = UserResponseSerializer(user).data
        
        return Response({
            'message': 'Registration successful. Please check your email to verify your account.',
            'user': user_data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def verify_email(request):
    """
    Verify email address with OTP.
    Endpoint: POST /api/auth/verify-email/
    """
    serializer = EmailVerificationSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        
        # Find user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if already verified
        if user.is_email_verified:
            return Response({
                'error': 'Email is already verified.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate OTP
        is_valid, error_message = validate_otp(user, otp, 'email_verification')
        
        if not is_valid:
            # Increment attempts if OTP is incorrect
            if error_message == 'Invalid OTP.':
                increment_otp_attempts(user, 'email_verification')
            
            return Response({
                'error': error_message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify email
        user.is_email_verified = True
        clear_otp(user, 'email_verification')
        user.save()
        
        return Response({
            'message': 'Email verified successfully. You can now log in.',
            'user': {
                'email': user.email,
                'is_email_verified': user.is_email_verified
            }
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def login(request):
    """
    Login and receive JWT tokens.
    Endpoint: POST /api/auth/login/
    """
    serializer = UserLoginSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        # Authenticate user
        user = authenticate(request, username=email, password=password)
        
        if user is None:
            return Response({
                'error': 'Invalid credentials.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Refresh user from database to ensure all fields are loaded
        user.refresh_from_db()
        
        # Check if email is verified
        if not user.is_email_verified:
            # Generate and send new OTP
            otp = generate_otp()
            user.email_verification_otp = otp
            user.email_verification_sent_at = timezone.now()
            user.email_verification_attempts = 0  # Reset attempts
            user.save()
            
            # Send verification email
            send_verification_email(user, otp)
            
            return Response({
                'error': 'Please verify your email before logging in.',
                'email_verified': False,
                'action': 'redirect_to_verification',
                'message': 'A new verification OTP has been sent to your email.',
                'otp_sent': True
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Prepare response
        user_data = UserResponseSerializer(user).data

        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user_data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout and delete tokens client-side.
    Endpoint: POST /api/auth/logout/
    """
    serializer = LogoutSerializer(data=request.data)
    
    if serializer.is_valid():
        return Response({
            'message': 'Logged out successfully.'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def password_reset_request(request):
    """
    Request password reset OTP via email.
    Endpoint: POST /api/auth/password-reset/request/
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        # Look up user (don't reveal if exists)
        try:
            user = User.objects.get(email=email)
            
            # Check if email is verified
            if not user.is_email_verified:
                # Check rate limiting
                if not can_resend_otp(user.email_verification_sent_at, cooldown_seconds=60):
                    return Response({
                        'error': 'Please wait 60 seconds before requesting a new OTP.'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)

                # Send email verification OTP instead
                otp = generate_otp()
                user.email_verification_otp = otp
                user.email_verification_sent_at = timezone.now()
                user.email_verification_attempts = 0
                user.save()
                
                send_verification_email(user, otp)
                
                return Response({
                    'error': 'Please verify your email first.',
                    'email_verified': False,
                    'action': 'redirect_to_verification',
                    'message': 'A verification OTP has been sent to your email.',
                    'otp_sent': True
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check rate limiting
            if not can_resend_otp(user.password_reset_sent_at, cooldown_seconds=60):
                return Response({
                    'error': 'Please wait 60 seconds before requesting a new OTP.'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            # Generate and send password reset OTP
            otp = generate_otp()
            user.password_reset_otp = otp
            user.password_reset_sent_at = timezone.now()
            user.password_reset_attempts = 0  # Reset attempts
            user.save()
            
            # Send password reset email
            send_password_reset_email(user, otp)
            
        except User.DoesNotExist:
            # Don't reveal if email doesn't exist (security)
            pass
        
        # Generic success message
        return Response({
            'message': 'If this email exists, a password reset OTP has been sent to your email.'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def password_reset_confirm(request):
    """
    Reset password with OTP.
    Endpoint: POST /api/auth/password-reset/confirm/
    """
    print("Password Reset Confirm Data:", request.data) # Debug print
    # Force reload
    serializer = PasswordResetConfirmSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        
        # Find user
        try:
            user = User.objects.get(email=email)
            print(f"User found: {user.email}") # Debug print
            print(f"Stored OTP: {user.password_reset_otp}, Incoming OTP: {otp}") # Debug print
            print(f"OTP Sent At: {user.password_reset_sent_at}") # Debug print
        except User.DoesNotExist:
            print("User not found") # Debug print
            return Response({
                'error': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate OTP
        is_valid, error_message = validate_otp(user, otp, 'password_reset')
        print(f"OTP Validation Result: {is_valid}, Error: {error_message}") # Debug print
        
        if not is_valid:
            # Increment attempts if OTP is incorrect
            if error_message == 'Invalid OTP.':
                increment_otp_attempts(user, 'password_reset')
            
            return Response({
                'error': error_message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Reset password
        user.set_password(new_password)
        clear_otp(user, 'password_reset')
        user.save()
        
        return Response({
            'message': 'Password reset successful. Please log in with your new password.'
        }, status=status.HTTP_200_OK)
    
    print("Serializer Errors:", serializer.errors) # Debug print
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def resend_verification(request):
    """
    Resend email verification OTP.
    Endpoint: POST /api/auth/resend-verification/
    """
    serializer = ResendVerificationSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        # Find user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if already verified
        if user.is_email_verified:
            return Response({
                'error': 'Email is already verified.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check rate limiting
        if not can_resend_otp(user.email_verification_sent_at, cooldown_seconds=60):
            return Response({
                'error': 'Please wait 60 seconds before requesting a new OTP.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Generate and send new OTP
        otp = generate_otp()
        user.email_verification_otp = otp
        user.email_verification_sent_at = timezone.now()
        user.email_verification_attempts = 0  # Reset attempts
        user.save()
        
        # Send verification email
        send_verification_email(user, otp)
        
        return Response({
            'message': 'A new verification OTP has been sent to your email.'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ========== USER PROFILE ENDPOINTS ==========

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Get or update current user profile.
    Endpoint: GET/PATCH /api/auth/user/profile/
    """
    user = request.user
    
    # Refresh user from database to ensure all fields are loaded
    user.refresh_from_db()
    
    if request.method == 'GET':
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PATCH':
        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            
            # Return updated profile
            response_serializer = UserProfileSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change password (authenticated).
    Endpoint: POST /api/auth/user/change-password/
    """
    user = request.user
    serializer = ChangePasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        current_password = serializer.validated_data['current_password']
        new_password = serializer.validated_data['new_password']
        
        # Check current password
        if not user.check_password(current_password):
            return Response({
                'error': 'Current password is incorrect.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        return Response({
            'message': 'Password changed successfully.'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



