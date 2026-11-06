# Shop FAQ Bot — REST API Documentation

Base URL: `http://localhost:5000/api` (Production: `https://<your-render-app>.onrender.com/api`)

All requests and responses use `application/json`.
Protected admin endpoints require the header:
```http
Authorization: Bearer <jwt_token>
```
Public customer chat endpoints require the header:
```http
X-Customer-Session: <session_token>
```

---

## 1. Authentication Endpoints

### 1.1 Register Shop Owner
- **URL**: `/api/auth/register`
- **Method**: `POST`
- **Auth Required**: No
- **Request Body**:
```json
{
  "full_name": "Ravi Kumar",
  "email": "ravi@gmail.com",
  "password": "password123",
  "confirm_password": "password123",
  "shop_name": "Ravi Mobiles",
  "slug": "ravi-mobiles",
  "description": "Smartphones and repairs"
}
```
- **Success Response** (`201 Created`):
```json
{
  "success": true,
  "message": "Registration successful",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsIn...",
    "user": {
      "id": 1,
      "full_name": "Ravi Kumar",
      "email": "ravi@gmail.com",
      "created_at": "2026-11-06T06:00:00Z"
    },
    "shop": {
      "id": 1,
      "owner_id": 1,
      "shop_name": "Ravi Mobiles",
      "slug": "ravi-mobiles",
      "description": "Smartphones and repairs",
      "created_at": "2026-11-06T06:00:00Z"
    }
  }
}
```

### 1.2 Login Shop Owner
- **URL**: `/api/auth/login`
- **Method**: `POST`
- **Auth Required**: No
- **Request Body**:
```json
{
  "email": "ravi@gmail.com",
  "password": "password123"
}
```
- **Success Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsIn...",
    "user": { ... },
    "shop": { ... }
  }
}
```

### 1.3 Get Current Profile
- **URL**: `/api/auth/me`
- **Method**: `GET`
- **Auth Required**: Yes (`Bearer <token>`)
- **Success Response** (`200 OK`):
```json
{
  "success": true,
  "data": {
    "user": { "id": 1, "email": "ravi@gmail.com", "full_name": "Ravi Kumar" },
    "shop": { "id": 1, "shop_name": "Ravi Mobiles", "slug": "ravi-mobiles" }
  }
}
```

---

## 2. Dashboard Endpoints

### 2.1 Get Dashboard Statistics
- **URL**: `/api/dashboard/stats`
- **Method**: `GET`
- **Auth Required**: Yes
- **Success Response** (`200 OK`):
```json
{
  "success": true,
  "data": {
    "stats": {
      "total_knowledge": 4,
      "total_questions": 12,
      "pending_questions": 2,
      "answered_questions": 10,
      "good_answers": 7,
      "bad_answers": 1
    },
    "shop": { "id": 1, "shop_name": "Ravi Mobiles", "slug": "ravi-mobiles" },
    "public_url": "http://localhost:5173/s/ravi-mobiles"
  }
}
```

### 2.2 Get Recent Questions & Activity
- **URL**: `/api/dashboard/recent-questions`
- **Method**: `GET`
- **Auth Required**: Yes
- **Success Response** (`200 OK`):
```json
{
  "success": true,
  "data": {
    "recent_questions": [ ... ],
    "recent_activities": [ ... ]
  }
}
```

---

## 3. Knowledge Base Endpoints

### 3.1 List Knowledge Entries
- **URL**: `/api/knowledge`
- **Method**: `GET`
- **Auth Required**: Yes
- **Query Params**:
  - `search` (optional string): Filter by query text
  - `category` (optional string): Filter by category
- **Success Response** (`200 OK`):
```json
{
  "success": true,
  "data": {
    "knowledge_entries": [
      {
        "id": 1,
        "shop_id": 1,
        "title": "Shop Timings",
        "content": "We open at 9 AM and close at 9 PM Monday to Saturday.",
        "category": "Timings",
        "source_type": "manual",
        "created_at": "2026-11-06T06:00:00Z"
      }
    ],
    "categories": ["Timings", "Products", "Policy"],
    "total": 1
  }
}
```

### 3.2 Create Knowledge Entry
- **URL**: `/api/knowledge`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "title": "Return Policy",
  "content": "Returns accepted within 7 days with original invoice.",
  "category": "Policy"
}
```

### 3.3 Update Knowledge Entry
- **URL**: `/api/knowledge/<id>`
- **Method**: `PUT`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "title": "Updated Return Policy",
  "content": "Returns accepted within 14 days with tags.",
  "category": "Policy"
}
```

### 3.4 Delete Knowledge Entry
- **URL**: `/api/knowledge/<id>`
- **Method**: `DELETE`
- **Auth Required**: Yes

---

## 4. Public Customer Chatbot Endpoints

### 4.1 Get Public Shop Info
- **URL**: `/api/public/shop/<slug>`
- **Method**: `GET`
- **Auth Required**: No
- **Success Response** (`200 OK`):
```json
{
  "success": true,
  "data": {
    "shop": {
      "id": 1,
      "shop_name": "Ravi Mobiles",
      "slug": "ravi-mobiles",
      "description": "Smartphones and repairs"
    }
  }
}
```

### 4.2 Initialize 36-Hour Customer Session
- **URL**: `/api/public/shop/<slug>/session`
- **Method**: `POST`
- **Auth Required**: No
- **Request Body**:
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com"
}
```
- **Success Response** (`201 Created`):
```json
{
  "success": true,
  "data": {
    "session_token": "48_char_secure_random_token",
    "expires_at": "2026-11-07T18:00:00Z",
    "customer": {
      "id": 1,
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com"
    },
    "conversation_id": 1
  }
}
```

### 4.3 Validate Customer Session
- **URL**: `/api/public/shop/<slug>/session/validate`
- **Method**: `GET`
- **Headers**: `X-Customer-Session: <token>`
- **Success Response** (`200 OK`):
```json
{
  "success": true,
  "data": {
    "valid": true,
    "customer": { ... },
    "expires_at": "2026-11-07T18:00:00Z",
    "messages": [ ... ]
  }
}
```

### 4.4 Send Customer Question
- **URL**: `/api/public/shop/<slug>/chat`
- **Method**: `POST`
- **Headers**: `X-Customer-Session: <token>`
- **Request Body**:
```json
{
  "message": "What time do you open?"
}
```
- **Success Response (When AI knows the answer)** (`200 OK`):
```json
{
  "success": true,
  "data": {
    "answer": "Our shop opens at 9 AM and closes at 9 PM Monday to Saturday.",
    "status": "answered",
    "can_answer": true,
    "question_id": 1,
    "timestamp": "2026-11-06T06:05:00Z"
  }
}
```
- **Fallback Response (When AI does not have sufficient knowledge)** (`200 OK`):
```json
{
  "success": true,
  "data": {
    "answer": "Thank you! The shop owner will reply to you soon by email.",
    "status": "pending",
    "can_answer": false,
    "question_id": 2,
    "timestamp": "2026-11-06T06:06:00Z"
  }
}
```

---

## 5. Customer Questions & Answer Endpoints

### 5.1 List Customer Questions
- **URL**: `/api/questions`
- **Method**: `GET`
- **Auth Required**: Yes
- **Query Params**: `status` (`pending` or `answered`)

### 5.2 Answer Pending Question & Dispatch Email
- **URL**: `/api/questions/<id>/answer`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "answer": "Yes, we provide home delivery within 5 km of our store.",
  "force_resend": false
}
```
- **Behavior**:
  1. Saves owner answer and marks question `status = 'answered'` immediately in the database.
  2. If an email notification was already successfully accepted previously (`email_status == 'sent'`), skips duplicate sending to avoid spamming the customer (unless `force_resend: true`).
  3. Dispatches the notification email using the configured provider (Resend or Gmail SMTP).
  4. Records the exact delivery status (`sent` or `failed`), error message, and delivery timestamp.
  5. **Automatically adds the question and approved answer to the shop's knowledge base** with `source_type = 'pending_answered'`.
  6. Creates audit entries in `activity_logs` and `email_notification_logs`.
- **Success Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Your reply has been saved and the email notification has been submitted successfully.",
  "data": {
    "question": {
      "id": 1,
      "status": "answered",
      "owner_answer": "Yes, we provide home delivery...",
      "email_status": "sent",
      "email_error": null,
      "email_retries": 1,
      "email_sent_at": "2026-11-06T12:00:00Z"
    },
    "email_status": "sent",
    "email_error": null
  }
}
```

### 5.3 Retry Failed Email Delivery
- **URL**: `/api/questions/<id>/retry-email`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body** (optional):
```json
{
  "force": false
}
```
- **Behavior**:
  1. Validates that the question belongs to the authenticated shop.
  2. Ensures an approved owner answer exists.
  3. Re-attempts dispatch via the active email provider.
  4. Increments retry counter and records detailed error logs if rejected.
  5. Prevents duplicate sends if the email was already accepted (`force: true` allows resending).

---

## 6. Feedback & AI Quality Reinforcement

### 6.1 List Questions for Review
- **URL**: `/api/feedback`
- **Method**: `GET`
- **Auth Required**: Yes

### 6.2 Rate Answer Good
- **URL**: `/api/feedback/<id>/good`
- **Method**: `POST`
- **Auth Required**: Yes

### 6.3 Rate Answer Bad & Provide Correction
- **URL**: `/api/feedback/<id>/bad`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "reason": "Missing details about fast charging adapters",
  "correct_answer": "Yes, we sell 65W and 120W fast charging adapters for both Samsung and Apple."
}
```
- **Behavior**:
  1. Records negative feedback and reasoning for audit.
  2. **Automatically saves the corrected answer into the shop's knowledge base** with `source_type = 'feedback_correction'`.
  3. Subsequent questions on this topic retrieve the corrected answer immediately!

