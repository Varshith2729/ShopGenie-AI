# ShopGenie AI — Multi-Tenant AI Customer Support & Knowledge Management Platform (SaaS)

[![Tests](https://img.shields.io/badge/tests-61%20passed%2C%201%20skipped-emerald)](backend/tests/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite%20%2B%20Tailwind-61dafb)](frontend)
[![Backend](https://img.shields.io/badge/Backend-Python%20%2B%20Flask%20%2B%20SQLAlchemy-3776ab)](backend)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%2F%20Supabase-3ecf8e)](docs/database-schema.md)
[![AI Engine](https://img.shields.io/badge/AI-Google%20Gemini%203.8%20Flash%20%2F%20Claude%20Haiku%205.5-4285f4)](backend/app/services/ai_service.py)

---

## 1. Project Overview

**ShopGenie AI** is a production-ready, multi-tenant SaaS customer support and knowledge management platform that enables retail and local shop owners to automate customer inquiries 24/7 with strict tenant isolation, zero hallucination, automated email escalation, and continuous self-learning.

Every shop owner registers their business, configures their knowledge base (opening hours, brands, inventory, policies, services), and receives an immediate **unique public customer chat URL** (e.g. `http://localhost:5173/s/ravi-mobiles`).

Customers visit the link, enter their contact info once (persisted securely for 36 hours), and receive instant, factual answers derived exclusively from that shop's knowledge base. If the AI cannot answer confidently, it creates a pending inquiry ticket for the owner. When the owner answers via their admin dashboard:
1. The customer receives an immediate formatted email notification.
2. The customer can reply directly to the email, with replies automatically ingested into the owner's dashboard conversation thread via Gmail IMAP.
3. The owner's approved answer is **automatically learned into the shop's knowledge base**, making future customer inquiries about that topic immediately answerable by the AI.

---

## 2. Four Critical Mentor Enhancements

### 1. Automatic Knowledge Base Learning from Pending Answers
- **Atomic Database Transaction**: When an owner submits an answer to a Pending question, the Knowledge Base entry (`source_type="pending_answered"`) is persisted and flushed before the question status transitions to `"answered"`.
- **Tenant Association**: The knowledge entry is strictly associated with `shop_id`. Shop A's answers are NEVER added to or accessible by Shop B.
- **Duplicate Prevention**: Intelligently identifies existing FAQ entries by title and question content, updating timestamps and content rather than creating redundant duplicates.
- **Immediate AI Searchability**: Owner-approved answers and corrections receive priority scoring bonuses in the retrieval engine, superseding older general entries.
- **Untrusted Guess Prevention**: Only owner-approved answers become trusted knowledge base entries.

### 2. Strict Real Email Delivery Testing
- **Strict Test Assertions**: Tests 15 and 16 no longer accept ambiguous `"sent"` or `"failed"`. A successful email test strictly requires provider confirmation (`status == "sent"` and HTTP 200). Delivery failures must strictly cause test failure.
- **Separation of Mocks and Live SMTP**: Unit tests use controlled mocks to verify error states, headers, and payload structures. Actual SMTP integration tests are segregated and triggered via `RUN_REAL_EMAIL_TESTS=true`.
- **Full SMTP Handshake & Logging**: Implements standard SMTP `EHLO -> STARTTLS -> EHLO -> login -> send_message` with SSL contexts, timeout handling, and diagnostic logging while strictly redacting passwords and keys.
- **Submission Distinction**: Accurately clarifies that SMTP acceptance confirms successful transport submission to the upstream mail server, avoiding false claims of customer mailbox receipt.

### 3. Automated Question Retry After Correction Regression Test
- Dedicated end-to-end regression test (`test_feedback_07_question_retry_after_correction_retrieves_approved_answer`):
  1. Creates Shop A with an initial return policy ("7 days with receipt").
  2. Customer asks an edge-case question ("Can I return items without receipt if they are unopened?").
  3. Bad answer feedback is submitted with customer notes.
  4. Owner submits approved correction ("Unopened sealed items can be returned within 14 days without receipt for store credit").
  5. Correction is saved to Knowledge Base (`source_type="feedback_correction"`).
  6. Customer asks the exact same question again.
  7. AI retrieves the corrected entry and returns the approved correction.
  8. Old outdated policy does NOT override the correction.
  9. Cross-tenant check: Shop B customer asking the same question receives fallback, proving zero data leakage.

### 4. Verified Current AI Model Configuration
- **Google Gemini**: Configured with Google's flagship Flash model `gemini-3.8-flash` (with optional `gemini-3.5-flash-lite`).
  - *Rationale*: Google's current Flash model offering high reasoning quality, rapid token latency, and cost efficiency for conversational customer support FAQ workloads.
  - *Verification Date*: November 21, 2026 via official Google AI documentation (`ai.google.dev`).
- **Anthropic Claude**: Configured with Anthropic's current fast model `claude-haiku-5-5` (with optional `claude-sonnet-5-5`).
  - *Verification Date*: November 21, 2026 via official Anthropic documentation (`docs.anthropic.com`).
- **Dynamic Environment Configuration**: Models are configured via `GEMINI_MODEL` and `CLAUDE_MODEL` in `backend/config.py` and `.env`, completely eliminating hardcoded model strings.

---

## 3. Technology Stack

- **Frontend**:
  - React 18
  - Vite 6
  - Tailwind CSS 3
  - React Router DOM 6
  - Axios (with JWT interceptors)
  - Lucide React Icons
- **Backend**:
  - Python 3.13 / 3.11+
  - Flask 3.1 & Flask-CORS
  - Flask-SQLAlchemy 3.1 & SQLAlchemy 2.0 ORM
  - Flask-Migrate & Alembic
  - PyJWT & Bcrypt (12-round salted hashing)
  - Pytest 9.1
- **Database**:
  - SQLite for instant local zero-config development (`instance/shop_faq.db`)
  - PostgreSQL (Supabase / Render PostgreSQL) for production
- **AI Providers**:
  - Google Gemini API (`gemini-3.8-flash`)
  - Anthropic Claude API (`claude-haiku-5-5`)
  - Intelligent context evaluator fallback for offline and deterministic testing
- **Email Infrastructure**:
  - Gmail SMTP (Port 587 with STARTTLS)
  - Gmail IMAP (Port 993 with SSL for incoming two-way reply synchronization)
  - Resend API
  - Development mock dispatcher with delivery failure tracking

---

## 4. Architecture & Workflows

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
        AuthMid[Auth & Tenant Isolation Middleware]
        SearchSvc[Relevance & Ranking Engine]
        AISvc[AI Provider: Gemini 3.8 Flash / Claude]
        EmailSvc[Notification Engine: Gmail SMTP / Resend]
        IMAPSvc[Inbound Sync: Gmail IMAP]
        DBORM[SQLAlchemy ORM Engine]
    end

    subgraph Storage [Supabase / PostgreSQL]
        DB[(Multi-Tenant Database)]
    end

    Cust -->|Visits /s/:slug| PubChat
    Owner -->|Manages Knowledge & Answers| AdminApp

    PubChat -->|Customer Session & Chat API| AuthMid
    AdminApp -->|Admin JWT APIs| AuthMid

    AuthMid --> SearchSvc
    SearchSvc -->|Filtered by shop_id| DBORM
    DBORM --> DB
    SearchSvc --> AISvc
    AISvc -->|Answers or Escalates to Pending| PubChat

    AdminApp -->|Answers Pending Inquiries| EmailSvc
    EmailSvc -->|Dispatches Email Notification| Cust
    Cust -->|Replies via Email| IMAPSvc
    IMAPSvc -->|Syncs Inbound Reply| AdminApp
```

---

## 5. Folder Structure

```
ShopGenie-AI/
├── backend/
│   ├── app/
│   │   ├── middleware/        # JWT auth, tenant scoping, rate limiting
│   │   ├── models/            # 10 SQLAlchemy models with shop_id scoping
│   │   ├── routes/            # auth, dashboard, knowledge, shop, customer, questions, feedback, email
│   │   ├── services/          # ai_service, email_service, email_sync_service, search_service
│   │   ├── utils/             # security, helpers, slugify
│   │   └── __init__.py        # Flask application factory & CORS
│   ├── tests/
│   │   ├── conftest.py        # Fixtures and in-memory test DB
│   │   ├── test_chatbot_intelligence.py   # Intent & sanitization tests
│   │   ├── test_comprehensive_suite.py    # Core 20 test suite with strict email checks
│   │   ├── test_email_service.py          # SMTP, Resend, and real delivery tests
│   │   ├── test_enhancements.py           # Auto-learning, retry regression, feedback, IMAP
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
│   │   ├── index.css          # Tailwind CSS
│   │   └── main.jsx           # React DOM root
│   ├── package.json           # Frontend dependencies
│   ├── vite.config.js         # Vite configuration with /api proxy
│   ├── tailwind.config.js     # Tailwind design system configuration
│   ├── vercel.json            # Vercel SPA rewrite rules
│   └── .env.example           # Frontend environment template
├── docs/                      # Architecture, Database Schema, API Docs
├── render.yaml                # Render deployment configuration
├── README.md                  # Project documentation
└── .gitignore                 # Git ignore patterns
```

---

## 6. Installation & Local Setup

### Prerequisites
- Python 3.10+ (Python 3.13 tested)
- Node.js 18+ & npm
- SQLite (included by default) or PostgreSQL

### 1. Clone & Setup Backend
```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure Environment (`backend/.env`)
```ini
# Database: Leave empty for SQLite, or provide PostgreSQL URL
DATABASE_URL=sqlite:///shop_faq.db

# Security
SECRET_KEY=shopgenie-super-secret-key-change-in-production
JWT_SECRET_KEY=shopgenie-jwt-secret-key-change-in-production

# AI Provider (gemini or claude)
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-3.8-flash
GEMINI_API_KEY=your_gemini_api_key_from_google_ai_studio

# Email Provider Configuration (Choose 'smtp' or 'resend')
EMAIL_PROVIDER=smtp
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_gmail@gmail.com
SMTP_PASSWORD=your_16_character_app_password
SMTP_USE_TLS=true
SMTP_TIMEOUT=10

# Two-Way Email Inbound Sync (Gmail IMAP)
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993

# Live Email Testing
RUN_REAL_EMAIL_TESTS=false
TEST_INBOX_EMAIL=your_test_inbox@gmail.com
```

### 3. Setup Frontend
```bash
cd ../frontend
npm install
npm run build
```

### 4. Seed Demo Shops
```bash
python backend/seed.py
```

### 5. Start Servers
- **Backend**:
  ```bash
  python backend/run.py
  ```
  Runs at `http://localhost:5000`
- **Frontend**:
  ```bash
  cd frontend
  npm run dev
  ```
  Runs at `http://localhost:5173`

---

## 7. Automated Testing & Verification

Run the full automated test suite (62 total scenarios):
```bash
python -m pytest backend/tests -v
```

### Test Suite Summary:
- **Core Multi-Tenant Suite (`test_comprehensive_suite.py`)**: 20 tests covering registration, login, unique slugs, public chatbot links, 36h session memory, multi-tenant knowledge retrieval, strict email trigger, and strict email retry.
- **Chatbot Intelligence Suite (`test_chatbot_intelligence.py`)**: 12 tests covering intent matching, semantic domain synonyms, empty/malformed AI output prevention, fallback triggering, and metadata sanitization.
- **Email Service Suite (`test_email_service.py`)**: 14 tests covering Resend dispatch, SMTP authentication, STARTTLS handshake, recipient validation, duplicate prevention, and optional live SMTP integration.
- **Enhancement Suite (`test_enhancements.py`)**: 16 tests covering customer feedback (good/bad), dashboard KPI updates, automatic knowledge base learning from pending answers, same-question retry after correction, IMAP inbound synchronization, and cross-shop isolation.

---

## 8. 5–10 Minute Mentor Demonstration Script

Use the seeded accounts or create new ones to demonstrate all features:

| Step | Action | Expected Result |
| :--- | :--- | :--- |
| **1. Multi-Tenant Accounts** | Sign in as **Shop A** (`ravi@gmail.com` / `password123`) in Browser 1. Sign in as **Shop B** (`sri@gmail.com` / `password123`) in an Incognito window. | Both owners see their own isolated dashboard, settings, and knowledge base. |
| **2. Unique Customer Links** | Copy link from Shop A dashboard (`/s/ravi-mobiles`) and Shop B dashboard (`/s/sri-fashion`). Open both in separate tabs. | Shop A displays Ravi Mobiles branding. Shop B displays Sri Fashion branding. |
| **3. Knowledge Isolation** | In Shop A, customer asks: *"What time do you open?"*<br>In Shop B, customer asks: *"What time do you open?"* | Shop A AI replies: *"Our shop opens at 9 AM and closes at 9 PM."*<br>Shop B AI replies: *"Our shop opens at 10 AM and closes at 8 PM."* (Zero cross-shop leak). |
| **4. Unknown Question -> Pending** | In Shop A chat, customer asks: *"Do you provide home delivery?"* | AI returns fallback: *"Thank you! The shop owner will reply to you soon by email."* Question is filed as Pending. |
| **5. Owner Answers Pending** | Shop A owner opens **Customer Questions** -> Pending. Enters: *"Yes, we provide free home delivery within 5 kilometres."* and clicks **Send Answer**. | 1. Status changes to Answered.<br>2. Real email notification is submitted to customer.<br>3. Original question and answer are **automatically added to Knowledge Base**. |
| **6. Verification of Learned Knowledge** | Customer in Shop A chat asks the exact same question again: *"Do you provide home delivery?"* | AI immediately retrieves the approved answer and replies: *"Yes, we provide free home delivery within 5 kilometres."* without human intervention! |
| **7. Cross-Shop Isolation on Learned Knowledge** | Customer in Shop B chat asks: *"Do you provide home delivery?"* | Shop B returns fallback! Shop B cannot access Shop A's learned delivery knowledge. |
| **8. Two-Way Email Reply** | Customer replies to the notification email in their Gmail inbox. Shop owner clicks **Sync Gmail** in dashboard. | Customer's incoming email response is ingested and displayed in the owner's conversation thread. |
| **9. Bad Answer Correction** | Customer asks a question on Shop A, rates the answer with 👎 Thumbs Down. Owner opens **Rate Answers**, clicks **Correct Answer**, and saves verified text. | Correction is saved under `AI Corrections`. Asking the same question immediately returns the corrected answer. |

---

## 9. Production Deployment Guide

### Database (PostgreSQL / Supabase)
1. Provision a PostgreSQL instance on Supabase or Render.
2. Set `DATABASE_URL=postgresql://user:password@host:port/dbname` in production environment.

### Backend (Render)
1. Link GitHub repository to Render using `render.yaml`.
2. Configure environment variables (`DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET_KEY`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `EMAIL_PROVIDER`, `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `FRONTEND_URL`).
3. Deploy service with Gunicorn: `gunicorn backend.run:app`.

### Frontend (Vercel)
1. Deploy the `frontend/` directory to Vercel.
2. Set environment variable: `VITE_API_BASE_URL=https://your-backend.onrender.com`.
3. Vercel automatically routes single-page application requests using `vercel.json`.

---

## 10. Security & Compliance

- **Multi-Tenant Protection**: Every database query is parameterized and strictly scoped by `shop_id`.
- **Password Security**: Passwords hashed with 12-round salted Bcrypt.
- **Session Protection**: Customer sessions are validated server-side using SHA-256 hashed 48-byte cryptographic tokens with a strict 36-hour expiry.
- **Redaction**: Zero passwords, app passwords, or API keys are ever printed in logs, test output, or public API responses.
