# Shop FAQ Bot — Multi-Tenant AI-Powered Customer Support SaaS

[![Tests](https://img.shields.io/badge/tests-58%20passed-emerald)](backend/tests/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite%20%2B%20Tailwind-61dafb)](frontend)
[![Backend](https://img.shields.io/badge/Backend-Python%20%2B%20Flask%20%2B%20SQLAlchemy-3776ab)](backend)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%2F%20Supabase-3ecf8e)](docs/database-schema.md)
[![AI Engine](https://img.shields.io/badge/AI-Google%20Gemini%20%2F%20Claude-4285f4)](backend/app/services/ai_service.py)

---

## 1. Project Overview

**Shop FAQ Bot** is a production-ready, multi-tenant SaaS application that enables retail and local shop owners to automate customer inquiries 24/7 using tailored Artificial Intelligence. 

Every shop owner registers their business, configures their knowledge base (hours, brands, returns, inventory, policies), and receives an immediate **unique public chatbot URL** (e.g. `http://localhost:5173/s/ravi-mobiles`). 

Customers visit the link, enter their contact info once (persisted securely for 36 hours), and receive instant, factual answers derived exclusively from that shop's knowledge base. If the AI cannot answer confidently, it creates a pending inquiry ticket for the owner, who can respond via the dashboard to automatically notify the customer by email and update the AI's knowledge base for future shoppers.

---

## 2. Problem Statement

Small-to-medium retail shops, electronics stores, boutiques, and pharmacies receive dozens of repetitive inquiries daily via phone calls, WhatsApp messages, and Instagram DMs regarding:
- *What time do you open or close today?*
- *Do you accept returns, and within how many days?*
- *Do you have iPhone 15 or OnePlus 12 in stock?*
- *Do you offer home delivery or gift wrapping?*

When staff are busy assisting in-store shoppers, digital inquiries go unanswered for hours, causing lost sales. Standard chatbots often hallucinate prices or invent policies. **Shop FAQ Bot solves this by combining strict tenant isolation, verified knowledge retrieval, and an automated owner escalation loop with email dispatch.**

---

## 3. Features

- **Multi-Tenant Architecture**: Complete logical and data separation for unlimited shop owners. Zero cross-shop data leakage.
- **Unique Public Chatbot URLs**: Custom vanity slugs (e.g. `/s/ravi-mobiles`, `/s/sri-fashion`) with real-time clipboard copy and live preview.
- **36-Hour Customer Session Memory**: Customers provide name and email once. Sessions persist across browser reloads for 36 hours.
- **Strict Factual AI Retrieval Engine**:
  - Grounded exclusively in the tenant's knowledge base.
  - Zero hallucination guardrails via system prompts and relevance thresholds.
  - If information is missing, returns the exact required fallback: *"Thank you! The shop owner will reply to you soon by email."* and creates a pending ticket.
- **Pending Questions & Automated Two-Way Email Communication**:
  - Shop owners answer unresolved inquiries directly in their admin dashboard.
  - Customers receive an immediate formatted email with clean headers (`In-Reply-To`, `References`, and `[Ref: #SG-{id}]`).
  - **Two-Way Reply Ingestion**: When customers click Reply in Gmail/email, their response is automatically ingested via **Gmail IMAP synchronization** or **Inbound Webhook** and attached to the conversation thread.
  - Shop owners can review the back-and-forth conversation history and send follow-up replies directly from the dashboard.
- **Customer Answer Feedback in Public Chatbot**:
  - Customers can rate AI responses as 👍 Good Answer or 👎 Bad Answer inline directly in the chat widget.
  - Bad answer feedback allows customers to provide an optional explanation.
  - The Owner Dashboard includes a dedicated **Rate Answers** portal with KPI counters, filter tabs, and a one-click **"Correct Answer"** modal to save verified corrections directly into the shop's Knowledge Base.
- **Natural, Professional Chatbot Display**:
  - Internal retrieval metadata, document headers (e.g., `[Entry 1 - Customer FAQ]`), and prompt formatting tags are strictly stripped before reaching the customer.
  - Chatbot responds in polite, complete, natural sentences.
- **Modern SaaS Admin Dashboard**: Overview metrics, knowledge management, question tables, activity logs, and mobile-responsive layout.

---

## 4. Technology Stack

- **Frontend**:
  - React 18
  - Vite 6
  - Tailwind CSS 3
  - React Router DOM 6
  - Axios
  - Lucide React Icons
- **Backend**:
  - Python 3.13 / 3.11+
  - Flask 3.1 & Flask-CORS
  - Flask-SQLAlchemy 3.1 & SQLAlchemy 2.0 ORM
  - Flask-Migrate & Alembic
  - PyJWT & Bcrypt (Password hashing)
  - Pytest & Httpx
- **Database**:
  - PostgreSQL (Supabase / Render PostgreSQL)
  - SQLite fallback for zero-configuration local development
- **AI Providers**:
  - Google Gemini 1.5 Flash (Default)
  - Anthropic Claude 3 Haiku (Configurable alternative)
  - Local intelligent rule-based evaluation fallback for offline testing
- **Email Infrastructure**:
  - Resend API
  - Standard SMTP (Gmail, SendGrid, Mailgun)
  - Development mock dispatcher with delivery failure tracking and retry
- **Deployment**:
  - Frontend: Vercel (`vercel.json` SPA configuration included)
  - Backend: Render (`render.yaml` blueprint included)
  - Database: Supabase PostgreSQL

---

## 5. System Architecture

```mermaid
flowchart TD
    subgraph Clients
        Cust[Customer Browser / Mobile]
        Owner[Shop Owner Dashboard]
    end

    subgraph Frontend [React + Vite SPA on Vercel]
        PubChat[Public Chatbot /s/:slug]
        AdminApp[Protected Tenant Admin Portal]
    end

    subgraph Backend [Flask REST API on Render]
        AuthMid[Auth & Tenant Middleware]
        SearchSvc[Search & Relevance Engine]
        AISvc[AI Provider: Gemini / Claude]
        EmailSvc[Notification Engine: Resend / SMTP]
        DBORM[SQLAlchemy ORM Engine]
    end

    subgraph Storage [Supabase / PostgreSQL]
        DB[(Multi-Tenant PostgreSQL Database)]
    end

    Cust -->|Visits /s/:slug| PubChat
    Owner -->|Manages KB & Answers| AdminApp

    PubChat -->|Customer Session & Chat API| AuthMid
    AdminApp -->|Admin JWT APIs| AuthMid

    AuthMid --> SearchSvc
    SearchSvc -->|Filtered by shop_id| DBORM
    DBORM --> DB
    SearchSvc --> AISvc
    AISvc -->|Generates Answer or Fallback| PubChat

    AdminApp -->|Answers Pending Inquiries| EmailSvc
    EmailSvc -->|Dispatches Email Notification| Cust
```

---

## 6. Database ER Diagram

```mermaid
erDiagram
    users ||--o{ shops : "owns"
    users ||--o{ activity_logs : "performed_by"

    shops ||--o{ knowledge_base : "contains"
    shops ||--o{ customers : "has"
    shops ||--o{ customer_sessions : "maintains"
    shops ||--o{ conversations : "logs"
    shops ||--o{ messages : "stores"
    shops ||--o{ customer_questions : "tracks"
    shops ||--o{ answer_feedback : "rates"
    shops ||--o{ activity_logs : "records"

    customers ||--o{ customer_sessions : "initiates"
    customers ||--o{ conversations : "participates_in"
    customers ||--o{ customer_questions : "asks"

    customer_sessions ||--o{ conversations : "authenticates"
    conversations ||--o{ messages : "contains"
    conversations ||--o{ customer_questions : "generates"

    customer_questions ||--o{ answer_feedback : "evaluated_by"
```

For full column descriptions, index definitions, and constraints, see [docs/database-schema.md](docs/database-schema.md).

---

## 7. Folder Structure

```
shop-faq-bot/
├── backend/
│   ├── app/
│   │   ├── middleware/        # JWT auth, tenant scoping, rate limiting
│   │   ├── models/            # 10 SQLAlchemy models with shop_id scoping
│   │   ├── routes/            # auth, dashboard, knowledge, shop, customer, questions, feedback
│   │   ├── services/          # ai_service, email_service, search_service
│   │   ├── utils/             # security, helpers, slugify
│   │   └── __init__.py        # Flask application factory & CORS
│   ├── tests/
│   │   ├── conftest.py        # Fixtures and in-memory test DB
│   │   ├── test_comprehensive_suite.py # 20 automated tests
│   │   └── run_tests.py       # Standalone test runner
│   ├── config.py              # Configuration & environment loader
│   ├── run.py                 # Backend entry point
│   ├── seed.py                # Demo seed script (Ravi Mobiles & Sri Fashion)
│   ├── requirements.txt       # Python dependencies
│   └── .env.example           # Backend environment template
├── frontend/
│   ├── src/
│   │   ├── context/           # AuthContext (state, login, token refresh)
│   │   ├── layouts/           # AdminLayout with responsive sidebar
│   │   ├── pages/             # LandingPage, LoginPage, RegisterPage, PublicChatPage
│   │   │   └── admin/         # Dashboard, KnowledgeBase, Questions, RateAnswers, Settings
│   │   ├── services/          # Modular Axios API clients
│   │   ├── App.jsx            # React Router setup & protected routes
│   │   ├── index.css          # Tailwind CSS & custom animations
│   │   └── main.jsx           # React DOM root
│   ├── package.json           # Frontend dependencies
│   ├── vite.config.js         # Vite configuration with /api proxy
│   ├── tailwind.config.js     # Tailwind design system configuration
│   ├── vercel.json            # Vercel SPA rewrite rules
│   └── .env.example           # Frontend environment template
├── docs/
│   ├── architecture.md        # Architecture, workflows & sequence diagrams
│   ├── database-schema.md     # 10 database tables & ER diagram
│   └── api-documentation.md   # Complete REST API specifications
├── render.yaml                # Render deployment configuration
├── README.md                  # Project documentation
└── .gitignore                 # Git ignore patterns
```

---

## 8. Installation Instructions

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ & npm
- PostgreSQL database (or use local SQLite for instant setup)

### 1. Clone or Open Project
```bash
git clone <repository-url>
cd shop-faq-bot
```

### 2. Backend Setup
```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
cp .env.example .env
```

---

## 9. Environment Variables Setup

### Backend (`backend/.env`):
```ini
# Database: Supabase PostgreSQL (or leave empty to default to local SQLite)
DATABASE_URL=postgresql://postgres.ref:password@aws-0-region.pooler.supabase.com:6543/postgres

# Security
SECRET_KEY=super-secret-key-change-me
JWT_SECRET_KEY=super-jwt-secret-key-change-me

# AI Configuration (gemini or claude)
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_claude_api_key_here

# Email Configuration (Choose EITHER Resend OR Gmail SMTP)
EMAIL_PROVIDER=resend

# Option A: Resend API
RESEND_API_KEY=re_your_resend_api_key
MAIL_FROM=onboarding@resend.dev

# Option B: Gmail / Standard SMTP
# EMAIL_PROVIDER=smtp
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=your_email@gmail.com
# SMTP_PASSWORD=your_16_character_app_password
# SMTP_USE_TLS=true
# SMTP_TIMEOUT=10

# URLs
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:5000
CUSTOMER_SESSION_HOURS=36
```

### Frontend (`frontend/.env`):
```ini
# Leave blank in development to use Vite's built-in /api proxy
VITE_API_BASE_URL=http://localhost:5000
```

---

## 10. Database Setup & Seeding

The application creates all required tables on startup automatically. To seed the database with the two demo shops:

```bash
python backend/seed.py
```
This populates:
1. **Shop A (Ravi Mobiles)**:
   - Slug: `ravi-mobiles`
   - Owner Email: `ravi@gmail.com`
   - Password: `password123`
   - Pre-seeded Knowledge: Open 9 AM to 9 PM, sells Samsung & Apple phones, 7-day returns.
2. **Shop B (Sri Fashion)**:
   - Slug: `sri-fashion`
   - Owner Email: `sri@gmail.com`
   - Password: `password123`
   - Pre-seeded Knowledge: Open 10 AM to 8 PM, sells men's & women's clothing, 5-day returns.

---

## 11. AI Provider Setup

### Using Google Gemini (Default)
1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/).
2. Set in `backend/.env`:
   ```ini
   AI_PROVIDER=gemini
   GEMINI_API_KEY=AIzaSy...
   ```

### Using Anthropic Claude (Alternative)
1. Obtain an API key from [Anthropic Console](https://console.anthropic.com/).
2. Set in `backend/.env`:
   ```ini
   AI_PROVIDER=claude
   ANTHROPIC_API_KEY=sk-ant-...
   ```

*Note: If no API key is provided, the backend seamlessly falls back to a deterministic, intelligent context extractor so the application and all automated tests run out-of-the-box offline!*

---

## 12. Email Provider Setup

### Option 1: Using Resend (Recommended)
1. Sign up at [Resend.com](https://resend.com) and generate an API key in **API Keys**.
2. Set in `backend/.env`:
   ```ini
   EMAIL_PROVIDER=resend
   RESEND_API_KEY=re_your_api_key_here
   MAIL_FROM=onboarding@resend.dev
   ```
   > **Note on Resend Free / Sandbox Accounts:** If your domain is not verified on Resend, Resend strictly allows sending **ONLY from `onboarding@resend.dev`** and **ONLY to your registered Resend account email**. To deliver emails to arbitrary customer addresses, verify a domain in the Resend dashboard and update `MAIL_FROM=support@yourverifieddomain.com`.

### Option 2: Using Gmail SMTP
1. Enable **2-Step Verification** on your Google Account.
2. Go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and create a **16-character App Password**.
3. Set in `backend/.env`:
   ```ini
   EMAIL_PROVIDER=smtp
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_16_character_app_password
   SMTP_USE_TLS=true
   SMTP_TIMEOUT=10
   ```
   > **Note:** Gmail App Passwords work immediately without domain verification, making it ideal for testing live inbox delivery to any customer email address!

---

## 13. Running the Application Locally

### 1. Start the Flask Backend:
```bash
python backend/run.py
```
The backend API starts on `http://localhost:5000`.

### 2. Start the React Frontend:
```bash
cd frontend
npm run dev
```
The frontend starts on `http://localhost:5173`.

---

## 14. Running Automated Tests

Run the complete 20-test automated test suite:
```bash
python backend/tests/run_tests.py
```
Or directly with pytest:
```bash
python -m pytest backend/tests/test_comprehensive_suite.py -v
```

### Test Coverage Checklist:
- [x] Test 1: Shop owner can register
- [x] Test 2: Shop owner can log in
- [x] Test 3: Duplicate email registration is rejected
- [x] Test 4: Owner can add knowledge
- [x] Test 5: Owner can edit knowledge
- [x] Test 6: Owner can delete knowledge
- [x] Test 7: Each shop receives a unique slug
- [x] Test 8: Customer can access the correct shop chatbot
- [x] Test 9: Customer session persists after reload
- [x] Test 10: Customer session expires after 36 hours
- [x] Test 11: AI retrieves only the current shop's knowledge
- [x] Test 12: AI returns fallback for unknown questions
- [x] Test 13: Unknown questions are saved as Pending
- [x] Test 14: Owner can answer pending questions
- [x] Test 15: Email is triggered after an answer
- [x] Test 16: Failed emails can be retried
- [x] Test 17: Good feedback is saved
- [x] Test 18: Bad feedback is saved
- [x] Test 19: Correct answers are added to the knowledge base
- [x] Test 20: Shop A cannot access Shop B's information (strict tenant isolation)

---

## 15. Complete Demo Walkthrough (Section 18)

Follow these steps to demonstrate the end-to-end multi-tenant lifecycle:

1. **Visit Landing Page**: Open `http://localhost:5173` to view the SaaS features and how it works.
2. **Login to Shop A**: Go to `/login` and click **"Ravi Mobiles"** demo button (`ravi@gmail.com` / `password123`).
3. **Inspect Knowledge Base**: Click **Knowledge Base** in the sidebar. Note: Opening hours (9 AM - 9 PM) and smartphone brands.
4. **Open Ravi Mobiles Chatbot**: Click **"Open Chatbot"** in the top navigation (`http://localhost:5173/s/ravi-mobiles`).
   - Enter Customer Details: `Alex Brown`, `alex@test.com`.
   - Ask: *"What time do you open?"*
   - Response: *"Our shop opens at 9 AM and closes at 9 PM."*
5. **Open Sri Fashion Chatbot**: Open a new tab to `http://localhost:5173/s/sri-fashion`.
   - Enter Customer Details: `Bella Green`, `bella@test.com`.
   - Ask: *"What time do you open?"*
   - Response: *"Our shop opens at 10 AM and closes at 8 PM."*
   - *Proves strict tenant isolation: Shop A returns 9 AM, Shop B returns 10 AM.*
6. **Trigger Pending Question Escalation**:
   - In Ravi Mobiles chat, ask: *"Do you provide home delivery?"*
   - Since delivery is not in Ravi Mobiles' knowledge base, the bot replies:
     `"Thank you! The shop owner will reply to you soon by email."`
7. **Answer Pending Question**:
   - Switch back to Ravi Mobiles admin portal and click **Customer Questions**.
   - Notice the pending question from Alex Brown.
   - Click **"Answer Now"**, type: *"Yes, we provide home delivery within 5 km of our shop for free."*
   - Click **"Send Answer & Email"**.
   - The question is marked answered, the customer receives an email notification, and the answer is **automatically added to the Knowledge Base**.
8. **Verify Knowledge Improvement**:
   - Go to **Knowledge Base** -> Notice the new entry titled `FAQ: Do you provide home delivery?` with badge `Learned from Question`.
   - Go back to the customer chat and ask: *"Do you provide home delivery?"*
   - AI answers immediately without human escalation!
9. **Rate Answers & AI Correction**:
   - In admin, navigate to **Rate Answers**.
   - Rate an answer **Good** -> Stats update.
   - Click **Bad** on another answer -> Enter Reason: *"Missing fast charging details"* and Correct Answer: *"Yes, we sell 65W fast chargers."*
   - Click **"Save Correct Answer"** -> Automatically added under `AI Corrections`. Future answers incorporate this correction.

---

## 16. Deployment Instructions

### 1. Database Deployment (Supabase)
1. Create a project at [database.new](https://database.new).
2. Go to **Project Settings** -> **Database** and copy the **URI connection string** (`Transaction` or `Session` pooler).
3. Set this as `DATABASE_URL` in your Render backend settings.

### 2. Backend Deployment (Render)
1. Push your code to GitHub.
2. In [Render Dashboard](https://dashboard.render.com), click **New +** -> **Blueprint**.
3. Select your repository. Render automatically reads `render.yaml`.
4. Configure your environment variables (`GEMINI_API_KEY`, `RESEND_API_KEY`, `FRONTEND_URL`).
5. Deploy service.

### 3. Frontend Deployment (Vercel)
1. In [Vercel Dashboard](https://vercel.com), click **Add New...** -> **Project**.
2. Select your repository and choose **Root Directory**: `frontend`.
3. Set Environment Variable:
   - `VITE_API_BASE_URL`: `https://your-backend.onrender.com`
4. Click **Deploy**. Vercel automatically uses `vercel.json` for SPA routing.

---

## 17. Security & Multi-Tenancy Architecture

1. **Tenant Isolation**:
   - Database queries are explicitly scoped with `filter_by(shop_id=...)`.
   - Admin access requires signed HS256 JWT tokens with verified shop ownership.
   - Cross-tenant modifications (e.g. attempting to edit another shop's knowledge entry) return HTTP 404 unauthorized.
2. **Secure Session Identifier**:
   - Customer session tokens are generated via `secrets.token_urlsafe(48)`.
   - Raw tokens are never stored plaintext; only SHA-256 hashes are persisted in the database.
   - Sessions expire strictly after 36 hours via server-side UTC timestamp comparisons.
3. **Credential Security**:
   - Passwords hashed with salted Bcrypt (12 rounds in production).
   - Zero API keys or secrets exposed to the frontend.
4. **Input Sanitization & Rate Limiting**:
   - In-memory rate limiting applied to session creation and chat endpoints to mitigate DDoS and spam.
   - SQL injection prevented through SQLAlchemy parameterized queries.

---

## 18. Git Commands to Push to GitHub

```bash
git init
git add .
git commit -m "feat: complete multi-tenant AI shop FAQ bot platform"
git branch -M main
git remote add origin https://github.com/your-username/shop-faq-bot.git
git push -u origin main
```

---

## 19. Demo Credentials

| Role | Shop Name | Email | Password | Public Chatbot URL |
| :--- | :--- | :--- | :--- | :--- |
| **Owner A** | Ravi Mobiles | `ravi@gmail.com` | `password123` | `http://localhost:5173/s/ravi-mobiles` |
| **Owner B** | Sri Fashion | `sri@gmail.com` | `password123` | `http://localhost:5173/s/sri-fashion` |

---

## 20. Known Limitations & Roadmap

- **Vector Search / Embeddings**: The current retrieval engine uses weighted keyword and phrase scoring across title, category, and content. Future versions can incorporate pgvector embeddings for deeper semantic similarity.
- **WhatsApp Webhook Integration**: Public chatbot links can be integrated directly with WhatsApp Business Cloud API webhooks.
- **Multi-Agent Routing**: Multiple sub-agents per shop for different departments (billing, hardware support, returns).

