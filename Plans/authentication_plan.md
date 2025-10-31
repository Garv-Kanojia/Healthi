# AUTHENTICATION PLAN - EDS ASSISTANT

**Project:** EDS Assistant Backend  
**Authentication Type:** JWT (JSON Web Tokens)  
**Framework:** Django + Django REST Framework + Simple JWT  
**Database:** PostgreSQL

---

## OVERVIEW

This plan outlines the complete authentication system for the EDS Assistant, using JWT tokens with email verification, password reset, and token refresh mechanisms.

---

## TECHNICAL STACK

### Core Libraries

- **Django** - Base framework
- **Django REST Framework (DRF)** - API framework
- **djangorestframework-simplejwt** - JWT implementation
- **django-cors-headers** - CORS support for future frontend
- **PostgreSQL** - Database

### Additional Dependencies

- **python-decouple** - Environment variable management
- **django-environ** - Enhanced environment configuration

---

## DATABASE SCHEMA

### 1. Custom User Model (`User`)

Extends Django's `AbstractUser`

```python
class User(AbstractUser):
    # Override default username - use email as unique identifier
    username = None  # Remove username field
    email = EmailField(unique=True, db_index=True)

    # Basic Information
    name = CharField(max_length=150)
    age = PositiveIntegerField(null=True, blank=True)
    gender = CharField(max_length=20, choices=GENDER_CHOICES, blank=True)

    # Authentication Fields
    is_email_verified = BooleanField(default=False)
    email_verification_otp = CharField(max_length=6, blank=True, null=True)  # 6-digit OTP
    email_verification_sent_at = DateTimeField(null=True, blank=True)
    email_verification_attempts = PositiveIntegerField(default=0)  # Track failed attempts

    # Password Reset Fields
    password_reset_otp = CharField(max_length=6, blank=True, null=True)  # 6-digit OTP
    password_reset_sent_at = DateTimeField(null=True, blank=True)
    password_reset_attempts = PositiveIntegerField(default=0)  # Track failed attempts

    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    last_login_at = DateTimeField(null=True, blank=True)

    # Settings
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
```

**Gender Choices:**

- Male
- Female
- Prefer not to say
- Other

### 2. Medical History Model (`MedicalHistory`)

Separate model for optional medical data (created post-registration)

```python
class MedicalHistory(Model):
    user = OneToOneField(User, on_delete=CASCADE, related_name='medical_history')

    # Medical Information - Single optional text field
    medical_notes = TextField(blank=True)  # User can add any medical history text

    # Metadata
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Note:** Medical history is completely optional to enetr at time of registration and can be added or updated anytime after successful login.

---

## PASSWORD POLICY

### Requirements

- **Minimum Length:** 8 characters
- **Maximum Length:** 16 characters
- **Must Include:**
  - At least one number (0-9)
  - At least one uppercase letter (A-Z)

### Implementation

Custom password validator in `validators.py`:

```python
class CustomPasswordValidator:
    def validate(self, password, user=None):
        # Check length (8-16 characters)
        if len(password) < 8 or len(password) > 16:
            raise ValidationError('Password must be between 8 and 16 characters.')

        # Check for at least one digit
        if not any(char.isdigit() for char in password):
            raise ValidationError('Password must contain at least one number.')

        # Check for at least one uppercase letter
        if not any(char.isupper() for char in password):
            raise ValidationError('Password must contain at least one uppercase letter.')
```

---

## JWT TOKEN CONFIGURATION

### Token Types

1. **Access Token**

   - Lifespan: 1 hour
   - Used for API authentication
   - Contains: user_id, email, exp, iat

2. **Refresh Token**
   - Lifespan: 7 days (1 week)
   - Used to obtain new access tokens
   - Stored securely, rotated on use

### Token Claims

```json
{
  "token_type": "access",
  "exp": 1234567890,
  "iat": 1234567890,
  "jti": "unique-token-id",
  "user_id": 123,
  "email": "user@example.com",
  "is_email_verified": true
}
```

### Token Storage Strategy

- **Access Token:** Sent in response, stored client-side in memory (recommended) or sessionStorage
- **Refresh Token:** Sent in HttpOnly cookie (recommended) or response body as fallback
- **Stateless JWT:** No database storage - pure JWT validation
- **No Token Blacklisting:** Tokens deleted client-side on logout (simpler approach)
- **Security Note:** HttpOnly cookies protect against XSS attacks; if using client-side storage, ensure proper XSS protection measures

---

## API ENDPOINTS

### Authentication Endpoints

#### 1. **POST /api/auth/register/**

Register a new user account

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "password_confirm": "SecurePass123",
  "name": "John Doe",
  "age": 28,
  "gender": "Male"
}
```

**Response (201 Created):**

```json
{
  "message": "Registration successful. Please check your email to verify your account.",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "age": 28,
    "gender": "Male",
    "is_email_verified": false,
    "created_at": "2025-10-31T10:00:00Z"
  }
}
```

**Response (409 Conflict - Email Already Exists but Unverified):**

```json
{
  "error": "This email is already registered but not verified.",
  "message": "Please go to the login page and attempt to login. You will be prompted to verify your email.",
  "action": "redirect_to_login",
  "email_verified": false
}
```

**Response (409 Conflict - Email Already Exists and Verified):**

```json
{
  "error": "This email is already registered and verified.",
  "message": "Please login with your credentials or use password reset if you forgot your password.",
  "action": "redirect_to_login",
  "email_verified": true
}
```

**Workflow:**

1. Validate input data
2. Check password policy compliance
3. **Check if email already exists in database**
   - If exists AND is_email_verified=True → Return 409 error with "redirect_to_login" action
   - If exists AND is_email_verified=False → Return 409 error with "redirect_to_login" action and message to login to trigger verification
   - If doesn't exist → Continue to step 4
4. Create user (is_email_verified=False)
5. Generate 6-digit random OTP (e.g., 123456)
6. Save OTP to user record with timestamp
7. Send OTP via email
8. Return user data (no tokens until verified)

**Note:** User must enter this OTP along with their email to verify their account.

---

#### 2. **POST /api/auth/verify-email/**

Verify email address with OTP

**Request Body:**

```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

**Response (200 OK):**

```json
{
  "message": "Email verified successfully. You can now log in.",
  "user": {
    "email": "user@example.com",
    "is_email_verified": true
  }
}
```

**Response (400 Bad Request - Invalid OTP):**

```json
{
  "error": "Invalid or expired OTP."
}
```

**Response (400 Bad Request - OTP Expired):**

```json
{
  "error": "OTP has expired. Please request a new one."
}
```

**Workflow:**

1. Find user by email address
2. Validate OTP matches the stored OTP
3. Check OTP expiry (1 hour from sent_at)
4. Check if attempts exceed limit (3 maximum)
   - If attempts >= 3 → Clear OTP, return error
   - If OTP invalid → Increment email_verification_attempts counter
5. Update is_email_verified=True
6. Clear verification OTP from database
7. Reset email_verification_attempts to 0
8. Return success message

**Security Notes:**

- Maximum 3 OTP verification attempts before requiring new OTP
- Failed attempts tracked in `email_verification_attempts` field
- OTP is case-sensitive (numbers only)
- OTP expires after 1 hour
- One-time use only (cleared after successful verification)

---

#### 3. **POST /api/auth/login/**

Login and receive JWT tokens

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response (200 OK):**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "age": 28,
    "gender": "Male",
    "is_email_verified": true
  }
}
```

**Response (403 Forbidden - Unverified Email):**

```json
{
  "error": "Please verify your email before logging in.",
  "email_verified": false,
  "action": "redirect_to_verification",
  "message": "A new verification OTP has been sent to your email.",
  "otp_sent": true
}
```

**Note:** When an unverified user attempts to login, the backend automatically generates and sends a new OTP to their email, then returns this response instructing the frontend to redirect to the verification page.

**Workflow:**

1. Validate credentials (email + password)
2. Check if email is verified
   - **If is_email_verified=False:**
     - Generate new 6-digit OTP
     - Save OTP to user record with current timestamp
     - Send OTP via email
     - Return 403 error with "redirect_to_verification" action
     - Frontend redirects user to verification page
   - **If is_email_verified=True:**
     - Continue to step 3
3. Generate access + refresh tokens
4. Update last_login_at
5. Return tokens and user data

---

#### 4. **POST /api/auth/token/refresh/**

Refresh access token using refresh token

**Request Body:**

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..." // New refresh token (rotation)
}
```

**Workflow:**

1. Validate refresh token
2. Generate new access token
3. Generate new refresh token (rotation for security)
4. Return both tokens

---

#### 5. **POST /api/auth/logout/**

Logout and delete tokens client-side

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body:**

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**

```json
{
  "message": "Logged out successfully."
}
```

**Workflow:**

1. Validate access token (optional check)
2. Return success message to client
3. **Client-side token deletion:**
   - Delete access token from memory/sessionStorage/localStorage
   - Delete refresh token from HttpOnly cookie (if using cookies) or client storage
   - Clear any cached user data
4. No server-side token invalidation (stateless approach)

**Implementation Note:**

- **Server-side:** Simple endpoint that returns success (no blacklisting)
- **Client-side:** Frontend must delete both tokens immediately after receiving response
- **Security:** Tokens are NOT invalidated on server (stateless JWT trade-off)
- **Risk:** If token was stolen before logout, it remains valid until expiry

---

#### 6. **POST /api/auth/password-reset/request/**

Request password reset OTP via email

**Request Body:**

```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**

```json
{
  "message": "If this email exists, a password reset OTP has been sent to your email."
}
```

**Response (403 Forbidden - Unverified Email):**

```json
{
  "error": "Please verify your email first.",
  "email_verified": false,
  "action": "redirect_to_verification",
  "message": "A verification OTP has been sent to your email.",
  "otp_sent": true
}
```

**Workflow:**

1. Look up user by email (don't reveal if exists for security)
2. **If user exists, check if email is verified:**
   - **If is_email_verified=False:**
     - Generate new 6-digit email verification OTP
     - Save OTP to user record with current timestamp
     - Send verification OTP via email
     - Return 403 error with "redirect_to_verification" action
     - Frontend redirects user to email verification page
   - **If is_email_verified=True:**
     - Continue to step 3
3. Generate 6-digit random password reset OTP
4. Store OTP and timestamp
5. Send password reset OTP via email
6. Return generic success message (security - don't reveal if email exists)

**Note:** OTP expires in 1 hour and can only be used once.

**Important:** Users with unverified emails CANNOT reset their password. They must verify their email first.

---

#### 7. **POST /api/auth/password-reset/confirm/**

Reset password with OTP

**Request Body:**

```json
{
  "email": "user@example.com",
  "otp": "654321",
  "password": "NewSecurePass456",
  "password_confirm": "NewSecurePass456"
}
```

**Response (200 OK):**

```json
{
  "message": "Password reset successful. Please log in with your new password."
}
```

**Response (400 Bad Request - Invalid OTP):**

```json
{
  "error": "Invalid or expired OTP."
}
```

**Workflow:**

1. Find user by email address
2. Validate OTP matches stored OTP
3. Check OTP expiry (1 hour from sent_at)
4. Check if attempts exceed limit (3 maximum)
   - If attempts >= 3 → Clear OTP, return error
   - If OTP invalid → Increment password_reset_attempts counter
5. Validate new password (policy compliance)
6. Update user password (hashed)
7. Clear reset OTP from database
8. Reset password_reset_attempts to 0
9. Return success message

**Security Notes:**

- Maximum 3 attempts to enter correct OTP
- Failed attempts tracked in `password_reset_attempts` field
- OTP is one-time use only
- All existing sessions/tokens remain valid after password reset

---

#### 8. **POST /api/auth/resend-verification/**

Resend email verification OTP

**Request Body:**

```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**

```json
{
  "message": "A new verification OTP has been sent to your email."
}
```

**Response (400 Bad Request - Already Verified):**

```json
{
  "error": "Email is already verified."
}
```

**Response (429 Too Many Requests - Rate Limit):**

```json
{
  "error": "Please wait 60 seconds before requesting a new OTP."
}
```

**Note:** This endpoint is optional for users who need to manually request a new OTP. However, in the updated flow, users typically get a new OTP automatically when they attempt to login with an unverified email.

**Workflow:**

1. Look up user by email
2. Check if already verified
3. Check rate limiting (60 seconds between resend requests)
4. Generate new 6-digit OTP
5. Update verification_sent_at timestamp
6. Reset email_verification_attempts to 0 (fresh start with new OTP)
7. Send new OTP via email
8. Return success message

**Rate Limiting:** User can request new OTP only once per minute to prevent abuse.

---

### User Profile Endpoints

#### 9. **GET /api/auth/user/profile/**

Get current user profile

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response (200 OK):**

```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "age": 28,
  "gender": "Male",
  "is_email_verified": true,
  "created_at": "2025-10-31T10:00:00Z",
  "has_medical_history": false
}
```

---

#### 10. **PATCH /api/auth/user/profile/**

Update user profile

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body (partial updates allowed):**

```json
{
  "name": "John Updated Doe",
  "age": 29,
  "gender": "Male"
}
```

**Response (200 OK):**

```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Updated Doe",
  "age": 29,
  "gender": "Male",
  "is_email_verified": true,
  "updated_at": "2025-10-31T12:00:00Z"
}
```

---

#### 11. **POST /api/auth/user/change-password/**

Change password (authenticated)

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body:**

```json
{
  "current_password": "OldPassword123",
  "new_password": "NewSecurePass456",
  "new_password_confirm": "NewSecurePass456"
}
```

**Response (200 OK):**

```json
{
  "message": "Password changed successfully."
}
```

---

### Medical History Endpoints

#### 12. **POST /api/auth/user/medical-history/**

Add/Update medical history (Optional - can be done anytime after login)

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body:**

```json
{
  "medical_notes": "Diagnosed with hEDS in 2020 by Dr. Smith. Experiencing POTS and MCAS. Currently on beta blockers and antihistamines. Allergic to Penicillin. Mother also has hEDS."
}
```

**Response (201 Created / 200 OK):**

```json
{
  "id": 1,
  "user": 1,
  "medical_notes": "Diagnosed with hEDS in 2020 by Dr. Smith. Experiencing POTS and MCAS. Currently on beta blockers and antihistamines. Allergic to Penicillin. Mother also has hEDS.",
  "created_at": "2025-10-31T10:00:00Z",
  "updated_at": "2025-10-31T10:00:00Z"
}
```

---

#### 13. **GET /api/auth/user/medical-history/**

Get user's medical history

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response (200 OK):**

```json
{
  "id": 1,
  "medical_notes": "Diagnosed with hEDS in 2020 by Dr. Smith. Experiencing POTS and MCAS. Currently on beta blockers and antihistamines. Allergic to Penicillin. Mother also has hEDS.",
  "created_at": "2025-10-31T10:00:00Z",
  "updated_at": "2025-10-31T10:00:00Z"
}
```

**Response (404 Not Found):**

```json
{
  "error": "Medical history not found."
}
```

---

## EMAIL TEMPLATES

### 1. Email Verification Email (OTP)

**Subject:** Your EDS Assistant Verification Code

```html
<!DOCTYPE html>
<html>
  <body>
    <h2>Welcome to EDS Assistant, {{ user.name }}!</h2>
    <p>Your email verification code is:</p>

    <div
      style="background-color: #f4f4f4; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 5px; margin: 20px 0;"
    >
      {{ otp }}
    </div>

    <p><strong>This code will expire in 1 hour.</strong></p>

    <p>To verify your email:</p>
    <ol>
      <li>Go to the verification page</li>
      <li>Enter your email: <strong>{{ user.email }}</strong></li>
      <li>Enter the code above</li>
    </ol>

    <p style="color: #888; font-size: 12px;">
      If you didn't create an account, please ignore this email.
    </p>
    <p style="color: #888; font-size: 12px;">
      This is an automated message, please do not reply.
    </p>
  </body>
</html>
```

**Plain Text Version:**

```
Welcome to EDS Assistant, {{ user.name }}!

Your email verification code is: {{ otp }}

This code will expire in 1 hour.

To verify your email:
1. Go to the verification page
2. Enter your email: {{ user.email }}
3. Enter the code above

If you didn't create an account, please ignore this email.
```

### 2. Password Reset Email (OTP)

**Subject:** Your EDS Assistant Password Reset Code

```html
<!DOCTYPE html>
<html>
  <body>
    <h2>Password Reset Request</h2>
    <p>Hi {{ user.name }},</p>
    <p>We received a request to reset your password.</p>

    <p>Your password reset code is:</p>

    <div
      style="background-color: #fff3cd; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 5px; margin: 20px 0; border: 2px solid #ffc107;"
    >
      {{ otp }}
    </div>

    <p><strong>This code will expire in 1 hour.</strong></p>

    <p>To reset your password:</p>
    <ol>
      <li>Go to the password reset page</li>
      <li>Enter your email: <strong>{{ user.email }}</strong></li>
      <li>Enter the code above</li>
      <li>Create your new password</li>
    </ol>

    <p style="color: #d9534f; font-weight: bold;">
      If you didn't request this, please ignore this email and your password
      will remain unchanged.
    </p>
    <p style="color: #888; font-size: 12px;">
      This is an automated message, please do not reply.
    </p>
  </body>
</html>
```

**Plain Text Version:**

```
Password Reset Request

Hi {{ user.name }},

We received a request to reset your password.

Your password reset code is: {{ otp }}

This code will expire in 1 hour.

To reset your password:
1. Go to the password reset page
2. Enter your email: {{ user.email }}
3. Enter the code above
4. Create your new password

If you didn't request this, please ignore this email.
```

---

## SECURITY MEASURES

### 1. Token Security

- **Access Token:** Short-lived (1 hour)
- **Refresh Token:** Longer-lived (7 days) with rotation
- **Refresh Token Storage:** HttpOnly cookies (recommended) to protect against XSS attacks
- **Token Rotation:** Enabled - new refresh token issued on each refresh request
- **No Token Blacklisting:** Stateless approach - compromised tokens remain valid until expiry
- **HTTPS Only:** Enforce in production to protect tokens in transit
- **Security Trade-off:** Stateless JWT (no blacklist) chosen for simplicity; if refresh token is compromised, it remains valid for up to 7 days

### 2. Password Security

- **Hashing:** Django's default PBKDF2 with SHA256
- **Validation:** Custom validator enforcing policy
- **No Plain Text:** Never store or log passwords always use encryption

### 3. Email Verification (OTP-Based)

- **Required:** Users cannot log in until verified
- **OTP Format:** 6-digit numeric code (e.g., 123456)
- **OTP Expiry:** 1 hour from sent_at timestamp
- **Generation:** Random 6-digit number (100000-999999)
- **Attempts Tracking:** `email_verification_attempts` field in User model
- **Maximum Attempts:** 3 failed attempts before OTP is invalidated and new one must be requested
- **Rate Limiting:** New OTP can be requested only once per minute
- **One-Time Use:** OTP is cleared from database after successful verification
- **Attempt Reset:** Counter resets to 0 when new OTP is requested or verification succeeds

### 4. Password Reset (OTP-Based)

- **OTP Format:** 6-digit numeric code (e.g., 654321)
- **OTP Expiry:** 1 hour from sent_at timestamp
- **Generation:** Random 6-digit number (100000-999999)
- **Attempts Tracking:** `password_reset_attempts` field in User model
- **Maximum Attempts:** 3 failed attempts before OTP is invalidated and new one must be requested
- **Generic Messages:** Don't reveal if email exists (security)
- **One-Time Use:** OTP cleared after successful password reset
- **Attempt Reset:** Counter resets to 0 when new OTP is requested or reset succeeds

### 5. Rate Limiting

- **Login Attempts:** Not implemented (intentionally omitted for demo project)
- **OTP Resend Requests:** Implemented - 60 seconds cooldown between requests
- **OTP Verification Attempts:** Maximum 3 attempts per OTP
- **Note:** Basic rate limiting for OTP operations to prevent abuse

### 6. CORS Configuration

- **Allowed Origins:** Configure for future frontend domains
- **Credentials:** Allow cookies for potential future use
- **Methods:** POST, GET, PATCH, PUT, DELETE, OPTIONS

### 7. Input Validation

- **Email Format:** Valid email regex
- **Age Range:** 1-120 years
- **SQL Injection:** ORM prevents by default
- **XSS Protection:** DRF serializers handle escaping

### 8. Token Expiry & Session Management

- **Access Token Expiry:** 1 hour - user stays logged in with valid refresh token
- **Refresh Token Expiry:** 7 days - **user must re-login after 7 days**
- **No Automatic Extension:** Refresh token is NOT extended, hard cutoff at 7 days
- **User Experience:** After 7 days, refresh token expires and user is logged out completely

---

## DJANGO SETTINGS CONFIGURATION

```python
# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,  # No blacklisting - stateless approach
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'UPDATE_LAST_LOGIN': True,
}

# Cookie settings for refresh token (HttpOnly for security)
SIMPLE_JWT_COOKIE_NAME = 'refresh_token'
SIMPLE_JWT_COOKIE_SECURE = not DEBUG  # True in production (HTTPS only)
SIMPLE_JWT_COOKIE_HTTPONLY = True  # Prevents JavaScript access (XSS protection)
SIMPLE_JWT_COOKIE_SAMESITE = 'Lax'  # CSRF protection

# Authentication Classes
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# Custom User Model
AUTH_USER_MODEL = 'authentication.User'

# Password Validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'authentication.validators.CustomPasswordValidator',
    },
]

# Email Configuration (Development)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # For testing
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # For production
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@edsassistant.com')

# CORS Settings (for future Vue.js frontend)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",  # Django test frontend
    "http://127.0.0.1:8000",
    # "http://localhost:3000",  # Uncomment for future Vue.js frontend
    # "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
```

---

## FILE STRUCTURE

```
edsassistant/
├── manage.py
├── edsassistant/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── authentication/
│   ├── __init__.py
│   ├── models.py              # User, MedicalHistory models
│   ├── serializers.py         # DRF serializers
│   ├── views.py              # API views
│   ├── urls.py               # Auth routes
│   ├── validators.py         # Password validator
│   ├── utils.py              # OTP generation, rate limiting utilities
│   ├── emails.py             # Email sending utilities
│   ├── permissions.py        # Custom permissions
│   ├── admin.py              # Admin configuration
│   ├── tests/
│   │   ├── test_models.py
│   │   ├── test_views.py
│   │   ├── test_authentication.py
│   │   ├── test_otp.py       # OTP generation and validation tests
│   │   └── test_permissions.py
│   └── templates/
│       └── emails/
│           ├── verify_email.html      # OTP verification email
│           └── password_reset.html    # OTP password reset email
└── requirements.txt
```

## ERROR HANDLING

### Standard Error Response Format

```json
{
  "error": "Error message here",
  "field_errors": {
    "email": ["This field is required."],
    "password": ["Password must contain at least one number."]
  },
  "status_code": 400
}
```

### Common Error Codes

- **400 Bad Request:** Invalid input data, validation errors
- **401 Unauthorized:** Missing or invalid token, token expired
- **403 Forbidden:** Email not verified, insufficient permissions
- **404 Not Found:** Resource doesn't exist (user, medical history)
- **409 Conflict:** Email already exists, email already verified
- **500 Internal Server Error:** Server error, database error

---

## DEPENDENCIES (requirements.txt)

```txt
Django==4.2.7
djangorestframework==3.14.0
djangorestframework-simplejwt==5.3.0
psycopg2-binary==2.9.9
python-decouple==3.8
django-environ==0.11.2
django-cors-headers==4.3.1
celery==5.3.4
redis==5.0.1
```

**Note:** Celery is included for future asynchronous task processing (email sending, background jobs). Redis will be used as Celery's message broker.

---

## ENVIRONMENT VARIABLES (.env)

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=edsassistant_db
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

# Email (for production)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@edsassistant.com

# Frontend URL (for email links in development)
FRONTEND_URL=http://localhost:8000
# For future Vue.js frontend, change to:
# FRONTEND_URL=http://localhost:3000

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-here

# Celery (for async tasks)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

---

## API DOCUMENTATION

---

## SECURITY CHECKLIST

- [x] JWT with short-lived access tokens (1 hour)
- [x] Refresh token rotation (7-day hard limit)
- [x] Email verification required before login (1-hour OTP expiry)
- [x] Password policy enforcement (8-16 chars, 1 number, 1 uppercase)
- [x] Password reset with expiring OTPs (1-hour expiry)
- [x] HTTPS enforcement (production)
- [x] CORS configuration
- [x] SQL injection prevention (ORM)
- [x] XSS protection (DRF serializers + HttpOnly cookies for refresh tokens)
- [x] Generic error messages (password reset)
- [x] Stateless JWT (no database token storage)
- [x] Medical data as optional single text field
- [x] OTP attempt tracking (email_verification_attempts and password_reset_attempts fields)
- [x] HttpOnly cookies for refresh tokens (XSS protection)
- [ ] Rate limiting (intentionally not implemented for demo)
- [ ] Testing suite (to be added later)
- [ ] Token blacklisting (trade-off: stateless simplicity over immediate revocation)

---

## NOTES

1. **Email Backend:** Use console backend for development (emails print to terminal), switch to SMTP for production
2. **Token Blacklisting:** Not implemented - using stateless JWT approach with client-side token deletion
3. **Medical History:** Single optional text field, can be added/updated anytime after successful login
4. **HTTPS:** Required in production for secure token transmission
5. **CORS:** Currently configured for Django test frontend (port 8000), update for Vue.js frontend (port 3000) later
6. **Celery:** Included for future async email sending, not required for initial development
7. **Test Frontend:** Basic HTML templates within Django for API testing, no separate Vue.js app yet
8. **Session Duration:** Hard 7-day limit on refresh tokens - users MUST re-login after 7 days
9. **Password Policy:** 8-16 characters, must include at least 1 number and 1 uppercase letter
10. **OTP Verification:** 6-digit numeric codes, 1-hour expiry, 3 attempts max (tracked in database), 60-second resend cooldown
11. **Email + OTP Required:** User must provide both email and OTP for verification/password reset
12. **Unverified Email Flow - Complete Scenarios:**
    - **Scenario 1 (Re-registration after closing tab):** User registers → closes tab → OTP expires (1 hour) → tries to register again → gets 409 error "email already registered but not verified" → redirects to login → login triggers new OTP and verification flow
    - **Scenario 2 (Login with unverified email):** User tries to login with correct credentials but unverified email → backend validates credentials → checks email verification status → generates new OTP → sends verification email → returns 403 with "redirect_to_verification" → frontend shows verification page
    - **Scenario 3 (Password reset with unverified email):** User clicks "Forgot Password" → enters unverified email → backend checks verification status → generates verification OTP (not password reset OTP) → sends verification email → returns 403 with "redirect_to_verification" → frontend shows verification page → user must verify email first before resetting password
13. **Refresh Token Storage:** HttpOnly cookies recommended for production (XSS protection); response body as fallback for development
14. **Stateless JWT Trade-off:** No token blacklisting means compromised tokens remain valid until expiry (max 7 days for refresh tokens)
15. **Email Verification Priority:** Email verification is ALWAYS enforced before any other operations (login, password reset)
