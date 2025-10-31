import random
from datetime import timedelta
from django.utils import timezone


def generate_otp():
    """
    Generate a random 6-digit OTP.
    Returns a string like '123456'
    """
    return str(random.randint(100000, 999999))


def is_otp_expired(sent_at, expiry_minutes=60):
    """
    Check if OTP has expired.
    
    Args:
        sent_at: DateTime when OTP was sent
        expiry_minutes: Expiry time in minutes (default: 60 minutes)
    
    Returns:
        True if expired, False otherwise
    """
    if not sent_at:
        return True
    
    expiry_time = sent_at + timedelta(minutes=expiry_minutes)
    return timezone.now() > expiry_time


def can_resend_otp(sent_at, cooldown_seconds=60):
    """
    Check if user can request a new OTP (rate limiting).
    
    Args:
        sent_at: DateTime when last OTP was sent
        cooldown_seconds: Cooldown period in seconds (default: 60 seconds)
    
    Returns:
        True if can resend, False otherwise
    """
    if not sent_at:
        return True
    
    cooldown_time = sent_at + timedelta(seconds=cooldown_seconds)
    return timezone.now() > cooldown_time


def validate_otp(user, otp, otp_type='email_verification'):
    """
    Validate OTP for a user.
    
    Args:
        user: User object
        otp: OTP string to validate
        otp_type: 'email_verification' or 'password_reset'
    
    Returns:
        Tuple (is_valid: bool, error_message: str)
    """
    if otp_type == 'email_verification':
        stored_otp = user.email_verification_otp
        sent_at = user.email_verification_sent_at
        attempts = user.email_verification_attempts
    elif otp_type == 'password_reset':
        stored_otp = user.password_reset_otp
        sent_at = user.password_reset_sent_at
        attempts = user.password_reset_attempts
    else:
        return False, 'Invalid OTP type.'
    
    # Check if OTP exists
    if not stored_otp:
        return False, 'No OTP found. Please request a new one.'
    
    # Check if OTP has expired
    if is_otp_expired(sent_at):
        return False, 'OTP has expired. Please request a new one.'
    
    # Check if maximum attempts exceeded
    if attempts >= 3:
        return False, 'Maximum attempts exceeded. Please request a new OTP.'
    
    # Validate OTP
    if stored_otp != otp:
        return False, 'Invalid OTP.'
    
    return True, ''


def clear_otp(user, otp_type='email_verification'):
    """
    Clear OTP and reset attempts counter.
    
    Args:
        user: User object
        otp_type: 'email_verification' or 'password_reset'
    """
    if otp_type == 'email_verification':
        user.email_verification_otp = None
        user.email_verification_sent_at = None
        user.email_verification_attempts = 0
    elif otp_type == 'password_reset':
        user.password_reset_otp = None
        user.password_reset_sent_at = None
        user.password_reset_attempts = 0
    
    user.save()


def increment_otp_attempts(user, otp_type='email_verification'):
    """
    Increment OTP verification attempts.
    
    Args:
        user: User object
        otp_type: 'email_verification' or 'password_reset'
    """
    if otp_type == 'email_verification':
        user.email_verification_attempts += 1
    elif otp_type == 'password_reset':
        user.password_reset_attempts += 1
    
    user.save()
