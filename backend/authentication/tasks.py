"""
Celery tasks for authentication app.

These tasks handle asynchronous email sending via SMTP.
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email_task(self, user_email, user_name, otp):
    """
    Celery task to send email verification OTP asynchronously.
    
    Args:
        user_email: User's email address
        user_name: User's display name
        otp: 6-digit OTP string
    """
    subject = 'Your EDS Assistant Verification Code'
    
    # HTML content
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2>Welcome to EDS Assistant, {user_name}!</h2>
        
        <p>Thank you for registering with EDS Assistant. To complete your registration, please verify your email address.</p>
        
        <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="margin: 0; font-size: 14px; color: #666;">Your verification code is:</p>
            <h1 style="margin: 10px 0; font-size: 32px; color: #007bff; letter-spacing: 5px;">{otp}</h1>
        </div>
        
        <p><strong>This code will expire in 1 hour.</strong></p>
        
        <p>To verify your email:</p>
        <ol>
            <li>Go to the verification page</li>
            <li>Enter your email: <strong>{user_email}</strong></li>
            <li>Enter the code above</li>
        </ol>
        
        <p style="color: #666; font-size: 14px; margin-top: 30px;">
            If you didn't create an account with EDS Assistant, please ignore this email.
        </p>
    </body>
    </html>
    """
    
    # Plain text version
    plain_message = f"""
Welcome to EDS Assistant, {user_name}!

Thank you for registering with EDS Assistant. To complete your registration, please verify your email address.

Your verification code is: {otp}

This code will expire in 1 hour.

To verify your email:
1. Go to the verification page
2. Enter your email: {user_email}
3. Enter the code above

If you didn't create an account with EDS Assistant, please ignore this email.
    """
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Verification email sent successfully to {user_email}")
        return True
    except Exception as exc:
        logger.error(f"Failed to send verification email to {user_email}: {exc}")
        # Retry the task on failure
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email_task(self, user_email, user_name, otp):
    """
    Celery task to send password reset OTP asynchronously.
    
    Args:
        user_email: User's email address
        user_name: User's display name
        otp: 6-digit OTP string
    """
    subject = 'Your EDS Assistant Password Reset Code'
    
    # HTML content
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2>Password Reset Request</h2>
        
        <p>Hi {user_name},</p>
        
        <p>We received a request to reset your password for your EDS Assistant account.</p>
        
        <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="margin: 0; font-size: 14px; color: #666;">Your password reset code is:</p>
            <h1 style="margin: 10px 0; font-size: 32px; color: #dc3545; letter-spacing: 5px;">{otp}</h1>
        </div>
        
        <p><strong>This code will expire in 1 hour.</strong></p>
        
        <p>To reset your password:</p>
        <ol>
            <li>Go to the password reset page</li>
            <li>Enter your email: <strong>{user_email}</strong></li>
            <li>Enter the code above</li>
            <li>Create your new password</li>
        </ol>
        
        <p style="color: #dc3545; margin-top: 20px;">
            <strong>Security Notice:</strong> If you didn't request this password reset, please ignore this email. 
            Your account remains secure.
        </p>
        
        <p style="color: #666; font-size: 14px; margin-top: 30px;">
            This is an automated message from EDS Assistant. Please do not reply to this email.
        </p>
    </body>
    </html>
    """
    
    # Plain text version
    plain_message = f"""
Password Reset Request

Hi {user_name},

We received a request to reset your password for your EDS Assistant account.

Your password reset code is: {otp}

This code will expire in 1 hour.

To reset your password:
1. Go to the password reset page
2. Enter your email: {user_email}
3. Enter the code above
4. Create your new password

Security Notice: If you didn't request this password reset, please ignore this email. Your account remains secure.

This is an automated message from EDS Assistant. Please do not reply to this email.
    """
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Password reset email sent successfully to {user_email}")
        return True
    except Exception as exc:
        logger.error(f"Failed to send password reset email to {user_email}: {exc}")
        # Retry the task on failure
        raise self.retry(exc=exc)
