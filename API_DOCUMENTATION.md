# EDS Assistant API Documentation

Base URL: `http://localhost:8000` (Development)

## Authentication Endpoints

### 1. Register User

Create a new user account. The user will receive an email with an OTP for verification.

- **URL:** `/api/auth/register/`
- **Method:** `POST`
- **Auth Required:** No
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123",
    "name": "John Doe",
    "age": 30, // Optional
    "gender": "Male" // Optional: "Male", "Female", "Prefer not to say", "Other"
  }
  ```
- **Success Response (201 Created):**
  ```json
  {
    "message": "Registration successful. Please check your email to verify your account.",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "name": "John Doe",
      "is_email_verified": false
    }
  }
  ```

### 2. Verify Email

Verify the user's email address using the OTP sent to their email.

- **URL:** `/api/auth/verify-email/`
- **Method:** `POST`
- **Auth Required:** No
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "otp": "123456"
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "message": "Email verified successfully. You can now log in.",
    "user": {
      "email": "user@example.com",
      "is_email_verified": true
    }
  }
  ```

### 3. Login

Authenticate a user and receive JWT access and refresh tokens.

- **URL:** `/api/auth/login/`
- **Method:** `POST`
- **Auth Required:** No
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123"
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "name": "John Doe",
      "is_email_verified": true
    }
  }
  ```

### 4. Refresh Token

Get a new access token using a valid refresh token.

- **URL:** `/api/auth/token/refresh/`
- **Method:** `POST`
- **Auth Required:** No
- **Request Body:**
  ```json
  {
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." // Optional, depending on settings
  }
  ```

### 5. Logout

Invalidate the user's session (client-side action mostly, but good practice to call).

- **URL:** `/api/auth/logout/`
- **Method:** `POST`
- **Auth Required:** Yes (Bearer Token)
- **Request Body:**
  ```json
  {
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "message": "Logged out successfully."
  }
  ```

### 6. Resend Verification OTP

Resend the email verification OTP if the previous one expired or was lost.

- **URL:** `/api/auth/resend-verification/`
- **Method:** `POST`
- **Auth Required:** No
- **Request Body:**
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "message": "A new verification OTP has been sent to your email."
  }
  ```

### 7. Password Reset Request

Request a password reset OTP via email.

- **URL:** `/api/auth/password-reset/request/`
- **Method:** `POST`
- **Auth Required:** No
- **Request Body:**
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "message": "If this email exists, a password reset OTP has been sent to your email."
  }
  ```

### 8. Password Reset Confirm

Reset the password using the OTP and new password.

- **URL:** `/api/auth/password-reset/confirm/`
- **Method:** `POST`
- **Auth Required:** No
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "otp": "123456",
    "password": "NewSecurePassword123",
    "confirm_password": "NewSecurePassword123"
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "message": "Password reset successful. Please log in with your new password."
  }
  ```

---

## User Profile Endpoints

### 1. Get User Profile

Retrieve the authenticated user's profile details.

- **URL:** `/api/auth/user/profile/`
- **Method:** `GET`
- **Auth Required:** Yes
- **Success Response (200 OK):**
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "age": 30,
    "gender": "Male",
    "is_email_verified": true,
    "created_at": "2023-11-19T10:00:00Z"
  }
  ```

### 2. Update User Profile

Update the authenticated user's profile details. You can also update your medical history notes here.

- **URL:** `/api/auth/user/profile/`
- **Method:** `PATCH`
- **Auth Required:** Yes
- **Request Body:** (All fields optional)
  ```json
  {
    "name": "Johnathan Doe",
    "age": 31,
    "medical_notes": "Patient has a history of EDS Type III..."
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "name": "Johnathan Doe",
    "age": 31,
    "gender": "Male",
    "medical_history": {
        "id": 1,
        "medical_notes": "Patient has a history of EDS Type III...",
        "created_at": "...",
        "updated_at": "..."
    },
    ...
  }
  ```

### 3. Change Password

Change the authenticated user's password.

- **URL:** `/api/auth/user/change-password/`
- **Method:** `POST`
- **Auth Required:** Yes
- **Request Body:**
  ```json
  {
    "current_password": "OldPassword123",
    "new_password": "NewPassword456",
    "confirm_password": "NewPassword456"
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "message": "Password changed successfully."
  }
  ```



---

## Chat Endpoints

### 1. List Chats

Get a list of all chat sessions for the user.

- **URL:** `/api/chats/`
- **Method:** `GET`
- **Auth Required:** Yes
- **Success Response (200 OK):**
  ```json
  {
    "success": true,
    "chats": [
      {
        "chat_id": "1700388000.123456",
        "name": "Chat 1",
        "created_at": "2023-11-19T10:00:00Z"
      },
      ...
    ]
  }
  ```

### 2. Create Chat

Start a new chat session. (Max 3 chats per user).

- **URL:** `/api/chats/`
- **Method:** `POST`
- **Auth Required:** Yes
- **Request Body:**
  ```json
  {
    "name": "New Consultation", // Optional, default: "Chat"
    "patient_info": "Age 30, Male, complaining of joint pain..." // Optional
  }
  ```
- **Success Response (201 Created):**
  ```json
  {
    "success": true,
    "message": "Chat created successfully",
    "chat": {
      "chat_id": "1700388000.123456",
      "name": "New Consultation",
      "patient_info": "...",
      "created_at": "..."
    }
  }
  ```

### 3. Get Chat Details

Retrieve a specific chat and its message history.

- **URL:** `/api/chats/<chat_id>/`
- **Method:** `GET`
- **Auth Required:** Yes
- **Success Response (200 OK):**
  ```json
  {
    "success": true,
    "chat": {
      "chat_id": "1700388000.123456",
      "name": "New Consultation",
      "messages": [
        {
          "prompt": "Hello",
          "response": "Hi there! How can I help you?",
          "created_at": "..."
        },
        ...
      ]
    }
  }
  ```

### 4. Update Chat Name

Rename a chat session.

- **URL:** `/api/chats/<chat_id>/`
- **Method:** `PATCH`
- **Auth Required:** Yes
- **Request Body:**
  ```json
  {
    "name": "Updated Chat Name"
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "success": true,
    "message": "Chat name updated successfully",
    "chat": { ... }
  }
  ```

### 5. Delete Chat

Delete a chat session and its associated memory.

- **URL:** `/api/chats/<chat_id>/`
- **Method:** `DELETE`
- **Auth Required:** Yes
- **Success Response (200 OK):**
  ```json
  {
    "success": true,
    "message": "Chat deleted successfully"
  }
  ```

### 6. Send Message (Query)

Send a message to the AI assistant.

- **URL:** `/api/chats/<chat_id>/query/`
- **Method:** `POST`
- **Auth Required:** Yes
- **Request Body:**
  - `query` (text): The user's message.
  - `files` (file upload, optional): List of files (images/PDFs).
- **Success Response (201 Created):**
  ```json
  {
    "success": true,
    "message": {
      "prompt": "What are the symptoms of EDS?",
      "response": "Ehlers-Danlos syndromes are a group of connective tissue disorders...",
      "created_at": "..."
    }
  }
  ```
