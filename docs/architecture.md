# System Architecture & Technical Specifications

## 1. High-Level Architecture Overview

Shop FAQ Bot is an enterprise-grade, multi-tenant SaaS platform that allows shop owners to provision customized AI-driven conversational assistants for their storefronts.

```mermaid
flowchart TD
    subgraph Clients
        Cust[Customer Browser / Mobile]
        Owner[Shop Owner Dashboard]
    end

    subgraph Frontend [React + Vite SPA on Vercel]
        PubChat[Public Chatbot Page /s/:slug]
        AdminApp[Protected Tenant Admin Portal]
    end

    subgraph Backend [Flask REST API on Render]
        AuthMid[Auth & Tenant Middleware]
        SearchSvc[Search & Relevance Engine]
        AISvc[AI Provider Engine: Gemini / Claude]
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

## 2. Multi-Tenant Isolation Strategy

Tenant isolation is built from the ground up at the database, business logic, and API gateway levels.

1. **Database-Level Isolation**:
   - Every tenant-specific table contains an indexed `shop_id` foreign key referencing `shops.id`.
   - All queries filter strictly by `shop_id`.
   - Cascading rules (`ondelete="CASCADE"`) guarantee that deleting a tenant purges all related sessions, messages, and knowledge without orphan leakages.

2. **Public Chatbot Slug Resolution**:
   - Customers never supply or control an internal database `shop_id`.
   - The backend validates the public URL slug (e.g., `/s/ravi-mobiles`), resolves the immutable internal `shop_id`, and validates session tokens against that specific `shop_id`.

3. **Admin JWT Token Validation**:
   - The JWT token contains `user_id` and `shop_id`.
   - The `@jwt_required` middleware validates the signature, queries the owner's shop, and assigns `g.current_shop`.
   - Admin routes only query `filter_by(shop_id=g.current_shop.id)`. Shop A can never read, modify, or delete Shop B's records.

---

## 3. AI Retrieval & Answering Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor Customer
    participant Frontend as Customer Chatbot
    participant Backend as Flask API
    participant Search as Relevance Engine
    participant AI as Gemini 1.5 Flash
    participant DB as PostgreSQL

    Customer->>Frontend: Types question ("What time do you open?")
    Frontend->>Backend: POST /api/public/shop/ravi-mobiles/chat
    Backend->>Backend: Validate 36-hr session token
    Backend->>Search: search_shop_knowledge(shop_id, query)
    Search->>DB: SELECT * FROM knowledge_base WHERE shop_id = ?
    DB-->>Search: Knowledge entries for shop
    Search-->>Backend: Ranked matching entries + relevance score

    alt Relevant Knowledge Found
        Backend->>AI: Send prompt with strict System Instruction + Context
        AI-->>Backend: JSON {"can_answer": true, "answer": "We open at 9 AM."}
        Backend->>DB: Save question (status='answered', ai_answer=...)
        Backend-->>Frontend: Return answer
        Frontend-->>Customer: Displays answer in chat
    else No Knowledge or Low Confidence
        Backend->>DB: Save question (status='pending', email_status='pending')
        Backend-->>Frontend: "Thank you! The shop owner will reply to you soon by email."
        Frontend-->>Customer: Displays exact fallback message
    end
```

---

## 4. Continuous Self-Improvement Loop

When the AI encounters a question it cannot answer, or provides an answer the owner considers suboptimal:

1. **Pending Question Workflow**:
   - The owner answers the pending question in the admin portal.
   - The customer receives an email notification with the answer.
   - The system **automatically inserts** the question and approved answer into the knowledge base (`source_type = 'pending_answered'`).
   - Subsequent customer inquiries on that topic are answered immediately by the AI.

2. **Rate Answers & Correction Workflow**:
   - The owner rates an AI response as **Bad**.
   - The owner inputs *Why is it bad?* and *What is the right answer?*.
   - The system records negative feedback audit trails and inserts the corrected knowledge into the knowledge base (`source_type = 'feedback_correction'`).
   - The AI uses this corrected knowledge for all future retrieval queries.

