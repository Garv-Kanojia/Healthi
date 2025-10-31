from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_verification_email(user, otp):
    """
    Send email verification OTP to user.
    
    Args:
        user: User object
        otp: 6-digit OTP string
    """
    subject = 'Your EDS Assistant Verification Code'
    
    # HTML content
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2>Welcome to EDS Assistant, {user.name}!</h2>
        
        <p>Thank you for registering with EDS Assistant. To complete your registration, please verify your email address.</p>
        
        <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="margin: 0; font-size: 14px; color: #666;">Your verification code is:</p>
            <h1 style="margin: 10px 0; font-size: 32px; color: #007bff; letter-spacing: 5px;">{otp}</h1>
        </div>
        
        <p><strong>This code will expire in 1 hour.</strong></p>
        
        <p>To verify your email:</p>
        <ol>
            <li>Go to the verification page</li>
            <li>Enter your email: <strong>{user.email}</strong></li>
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
Welcome to EDS Assistant, {user.name}!

Thank you for registering with EDS Assistant. To complete your registration, please verify your email address.

Your verification code is: {otp}

This code will expire in 1 hour.

To verify your email:
1. Go to the verification page
2. Enter your email: {user.email}
3. Enter the code above

If you didn't create an account with EDS Assistant, please ignore this email.
    """
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_password_reset_email(user, otp):
    """
    Send password reset OTP to user.
    
    Args:
        user: User object
        otp: 6-digit OTP string
    """
    subject = 'Your EDS Assistant Password Reset Code'
    
    # HTML content
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2>Password Reset Request</h2>
        
        <p>Hi {user.name},</p>
        
        <p>We received a request to reset your password for your EDS Assistant account.</p>
        
        <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="margin: 0; font-size: 14px; color: #666;">Your password reset code is:</p>
            <h1 style="margin: 10px 0; font-size: 32px; color: #dc3545; letter-spacing: 5px;">{otp}</h1>
        </div>
        
        <p><strong>This code will expire in 1 hour.</strong></p>
        
        <p>To reset your password:</p>
        <ol>
            <li>Go to the password reset page</li>
            <li>Enter your email: <strong>{user.email}</strong></li>
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

Hi {user.name},

We received a request to reset your password for your EDS Assistant account.

Your password reset code is: {otp}

This code will expire in 1 hour.

To reset your password:
1. Go to the password reset page
2. Enter your email: {user.email}
3. Enter the code above
4. Create your new password

Security Notice: If you didn't request this password reset, please ignore this email. Your account remains secure.

This is an automated message from EDS Assistant. Please do not reply to this email.
    """
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )
