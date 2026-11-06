import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load backend/.env first, then root .env if present
backend_dir = Path(__file__).resolve().parent
backend_env = backend_dir / ".env"
root_env = backend_dir.parent / ".env"

if backend_env.exists():
    load_dotenv(dotenv_path=backend_env, override=True)
if root_env.exists():
    load_dotenv(dotenv_path=root_env)
load_dotenv()  # Fallback to current working directory

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "shop-faq-bot-super-secret-key-change-in-production")
    
    # Database Configuration (PostgreSQL / Supabase default, SQLite fallback for local development)
    db_url = os.getenv("DATABASE_URL", "sqlite:///shop_faq.db")
    # Fix for SQLAlchemy requiring 'postgresql://' instead of 'postgres://' (common on Heroku/Render)
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT / Auth Configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    
    # AI Provider Configuration (gemini or claude)
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Email Configuration
    EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "").lower()
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    MAIL_FROM = os.getenv("MAIL_FROM", "onboarding@resend.dev")
    SMTP_SERVER = os.getenv("SMTP_SERVER", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", 10))
    IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
    INBOUND_REPLY_EMAIL = os.getenv("INBOUND_REPLY_EMAIL", "")
    INBOUND_WEBHOOK_SECRET = os.getenv("INBOUND_WEBHOOK_SECRET", "")
    
    # App URLs
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
    
    # Customer Session Duration (36 Hours)
    CUSTOMER_SESSION_HOURS = int(os.getenv("CUSTOMER_SESSION_HOURS", 36))

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    JWT_SECRET_KEY = "test-jwt-secret-key"
    AI_PROVIDER = "mock"
    EMAIL_PROVIDER = "mock"
    BCRYPT_ROUNDS = 4
