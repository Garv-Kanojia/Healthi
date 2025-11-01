# EDS Assistant - Authentication System

## Overview

This is the authentication backend for the EDS Assistant project, built with Django and Django REST Framework. The system implements JWT-based authentication with OTP email verification.

## ✅ Completed Implementation

### Core Components

1. **Custom User Model** (`authentication/models.py`)

   - Email-based authentication (no username)
   - OTP fields for email verification and password reset
   - User profile fields (name, age, gender)
   - Tracking fields (created_at, updated_at, last_login_at)

2. **Medical History Model** (`authentication/models.py`)

   - One-to-one relationship with User
   - Single text field for medical notes
   - Optional (can be added anytime after login)

3. **Password Validation** (`authentication/validators.py`)

   - 8-16 characters length
   - At least 1 number
   - At least 1 uppercase letter

4. **Utility Functions** (`authentication/utils.py`)

   - OTP generation (6-digit random code)
   - OTP validation and expiry checking
   - Rate limiting for OTP resend
   - Attempt tracking

5. **Email System** (`authentication/emails.py`)

   - Email verification emails with OTP
   - Password reset emails with OTP
   - HTML and plain text versions

6. **Serializers** (`authentication/serializers.py`)

   - Registration, login, verification
   - Password reset, profile management
   - Medical history CRUD

7. **API Endpoints** (`authentication/views.py`)

   - **Authentication:**

     - `POST /api/auth/register/` - Register new user
     - `POST /api/auth/verify-email/` - Verify email with OTP
     - `POST /api/auth/login/` - Login (returns JWT tokens)
     - `POST /api/auth/logout/` - Logout
     - `POST /api/auth/token/refresh/` - Refresh access token

   - **Password Reset:**

     - `POST /api/auth/password-reset/request/` - Request OTP
     - `POST /api/auth/password-reset/confirm/` - Reset password with OTP

   - **Verification:**

     - `POST /api/auth/resend-verification/` - Resend verification OTP

   - **User Profile:**

     - `GET /api/auth/user/profile/` - Get user profile
     - `PATCH /api/auth/user/profile/` - Update user profile
     - `POST /api/auth/user/change-password/` - Change password

   - **Medical History:**
     - `POST/PUT /api/auth/user/medical-history/` - Create/update medical history
     - `GET /api/auth/user/medical-history/` - Get medical history

8. **Django Admin** (`authentication/admin.py`)

   - Custom admin interface for User model
   - Medical History admin interface

9. **Settings Configuration** (`backend/settings.py`)
   - JWT configuration (1-hour access, 7-day refresh)
   - PostgreSQL database setup
   - CORS configuration
   - Email configuration (console backend for development)
   - Custom password validators

## 🔧 Setup Instructions

### Prerequisites

- Python 3.12+
- PostgreSQL (for production use)

### Installation Steps

1. **Activate Virtual Environment:**

   ```powershell
   .\auth_env\Scripts\activate
   ```

2. **Install Dependencies:**

   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**

   - Copy `.env.example` to `.env`
   - Update database credentials in `.env`:
     ```
     DB_NAME=edsassistant_db
     DB_USER=your_postgres_user
     DB_PASSWORD=your_postgres_password
     DB_HOST=localhost
     DB_PORT=5432
     ```

4. **Create PostgreSQL Database:**

   ```sql
   CREATE DATABASE edsassistant_db;
   ```

5. **Apply Migrations:**

   ```powershell
   python manage.py migrate
   ```

6. **Create Superuser (for admin access):**

   ```powershell
   python manage.py createsuperuser
   ```

7. **Run Development Server:**
   ```powershell
   python manage.py runserver
   ```

## 📝 Current Status

### ✅ Completed

- ✅ All models created (User, MedicalHistory)
- ✅ All 13 API endpoints implemented
- ✅ JWT authentication configured
- ✅ OTP-based email verification
- ✅ Password reset with OTP
- ✅ Custom password validation
- ✅ Django admin interface
- ✅ Serializers for all operations
- ✅ Email templates (HTML & plain text)
- ✅ Utility functions (OTP, rate limiting)
- ✅ URL routing configured
- ✅ Settings configured (JWT, CORS, email)
- ✅ Migrations created

### ⏳ Next Steps (Not in Current Scope)

1. **Setup PostgreSQL Database:**

   - Install PostgreSQL locally or use a cloud service
   - Create the database `edsassistant_db`
   - Update `.env` with correct credentials
   - Run migrations: `python manage.py migrate`

2. **Testing:**

   - Test all API endpoints using Postman or similar tool
   - Verify OTP emails (currently printing to console)
   - Test JWT token refresh flow

3. **Frontend Integration (Future):**

   - Build Vue.js or React frontend
   - Implement API calls to backend
   - Handle JWT token storage and refresh

4. **Production Deployment:**
   - Set up production PostgreSQL database
   - Configure production email backend (SMTP)
   - Set up Celery with Redis for async tasks
   - Deploy to cloud platform

## 🔐 Security Features

- JWT tokens with short-lived access (1 hour) and refresh (7 days)
- Email verification required before login
- OTP-based password reset (6-digit, 1-hour expiry)
- Maximum 3 OTP attempts before requiring new code
- Rate limiting on OTP resend (60-second cooldown)
- Password policy enforcement (8-16 chars, 1 number, 1 uppercase)
- CORS protection
- Stateless authentication (no token blacklisting)

## 📂 Project Structure

```
backend/
├── authentication/              # Authentication app
│   ├── migrations/             # Database migrations
│   ├── __init__.py
│   ├── admin.py               # Admin interface
│   ├── emails.py              # Email sending functions
│   ├── models.py              # User & MedicalHistory models
│   ├── serializers.py         # DRF serializers
│   ├── urls.py                # App URLs
│   ├── utils.py               # Utility functions
│   ├── validators.py          # Custom validators
│   └── views.py               # API endpoints
├── backend/                    # Project settings
│   ├── __init__.py
│   ├── settings.py            # Django settings
│   ├── urls.py                # Main URLs
│   ├── asgi.py
│   └── wsgi.py
├── manage.py                  # Django management script
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
└── .env                      # Environment variables (not in git)
```

## 🚀 API Documentation

For detailed API documentation, refer to the `authentication_plan.md` file in the `Plans/` folder.

### Quick Reference

**Base URL:** `http://localhost:8000/api/auth/`

**Authentication Header:**

```
Authorization: Bearer <access_token>
```

**Common Response Codes:**

- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Validation error
- `401 Unauthorized` - Invalid credentials
- `403 Forbidden` - Email not verified
- `404 Not Found` - Resource not found
- `409 Conflict` - Email already exists
- `429 Too Many Requests` - Rate limit exceeded

## 📧 Email Configuration

Currently using **console backend** for development (emails print to terminal).

For production, update `.env`:

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## 🔑 Environment Variables

See `.env.example` for all required environment variables.

## 📖 Additional Notes

1. **No Frontend Yet:** This is backend-only implementation. Testing should be done via API tools (Postman, curl, etc.)

2. **PostgreSQL Required:** The plan specifies PostgreSQL. Update `.env` with your database credentials.

3. **Email Verification:** Users MUST verify their email before logging in. OTP is sent to their email.

4. **Medical History Optional:** Users can add medical history anytime after successful login.

5. **Token Lifetime:**

   - Access token: 1 hour
   - Refresh token: 7 days (hard limit, user must re-login after 7 days)

6. **OTP Security:**
   - 6-digit numeric code
   - 1-hour expiry
   - Maximum 3 verification attempts
   - 60-second cooldown on resend requests

---

**Project:** EDS Assistant  
**Status:** Authentication Backend Complete ✅  
**Date:** October 31, 2025  
**Framework:** Django 4.2.7 + Django REST Framework 3.14.0
