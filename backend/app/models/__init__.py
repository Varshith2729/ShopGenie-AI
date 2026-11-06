from datetime import datetime, timezone
import uuid
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utcnow():
    return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    # Relationships
    shops = db.relationship("Shop", backref="owner", lazy=True, cascade="all, delete-orphan")
    activity_logs = db.relationship("ActivityLog", backref="user", lazy=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Shop(db.Model):
    __tablename__ = "shops"
    
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shop_name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    # Tenant Relationships (all scoped by shop_id)
    knowledge_entries = db.relationship("KnowledgeBase", backref="shop", lazy=True, cascade="all, delete-orphan")
    customers = db.relationship("Customer", backref="shop", lazy=True, cascade="all, delete-orphan")
    sessions = db.relationship("CustomerSession", backref="shop", lazy=True, cascade="all, delete-orphan")
    conversations = db.relationship("Conversation", backref="shop", lazy=True, cascade="all, delete-orphan")
    messages = db.relationship("Message", backref="shop", lazy=True, cascade="all, delete-orphan")
    questions = db.relationship("CustomerQuestion", backref="shop", lazy=True, cascade="all, delete-orphan")
    feedbacks = db.relationship("AnswerFeedback", backref="shop", lazy=True, cascade="all, delete-orphan")
    activities = db.relationship("ActivityLog", backref="shop", lazy=True, cascade="all, delete-orphan")
    email_logs = db.relationship("EmailNotificationLog", backref="shop", lazy=True, cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "shop_name": self.shop_name,
            "slug": self.slug,
            "description": self.description,
            "logo_url": self.logo_url,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class KnowledgeBase(db.Model):
    __tablename__ = "knowledge_base"
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False, default="General", index=True)
    source_type = db.Column(db.String(50), nullable=False, default="manual")  # manual, pending_answered, feedback_correction
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "shop_id": self.shop_id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "source_type": self.source_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Customer(db.Model):
    __tablename__ = "customers"
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(150), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    sessions = db.relationship("CustomerSession", backref="customer", lazy=True, cascade="all, delete-orphan")
    conversations = db.relationship("Conversation", backref="customer", lazy=True, cascade="all, delete-orphan")
    questions = db.relationship("CustomerQuestion", backref="customer", lazy=True, cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "shop_id": self.shop_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": f"{self.first_name} {self.last_name}".strip(),
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class CustomerSession(db.Model):
    __tablename__ = "customer_sessions"
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token_hash = db.Column(db.String(128), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    conversations = db.relationship("Conversation", backref="session", lazy=True)
    
    def is_expired(self):
        now = datetime.now(timezone.utc)
        # Normalize naive / aware
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now > exp

    def to_dict(self):
        return {
            "id": self.id,
            "shop_id": self.shop_id,
            "customer_id": self.customer_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Conversation(db.Model):
    __tablename__ = "conversations"
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey("customer_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    
    messages = db.relationship("Message", backref="conversation", lazy=True, cascade="all, delete-orphan", order_by="Message.created_at")
    questions = db.relationship("CustomerQuestion", backref="conversation", lazy=True)
    
    def to_dict(self, include_messages=False):
        data = {
            "id": self.id,
            "shop_id": self.shop_id,
            "customer_id": self.customer_id,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        if include_messages:
            data["messages"] = [m.to_dict() for m in self.messages]
        return data

class Message(db.Model):
    __tablename__ = "messages"
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_type = db.Column(db.String(20), nullable=False)  # 'customer', 'ai', 'owner'
    message_content = db.Column(db.Text, nullable=False)
    email_message_id = db.Column(db.String(255), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "shop_id": self.shop_id,
            "conversation_id": self.conversation_id,
            "sender_type": self.sender_type,
            "message_content": self.message_content,
            "email_message_id": self.email_message_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class CustomerQuestion(db.Model):
    __tablename__ = "customer_questions"
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    question = db.Column(db.Text, nullable=False)
    ai_answer = db.Column(db.Text, nullable=True)
    owner_answer = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)  # 'pending', 'answered', 'customer_replied'
    email_status = db.Column(db.String(30), nullable=False, default="not_applicable")  # 'not_applicable', 'pending', 'sent', 'failed'
    email_error = db.Column(db.Text, nullable=True)
    email_retries = db.Column(db.Integer, default=0, nullable=False)
    email_sent_at = db.Column(db.DateTime, nullable=True)
    email_provider = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    answered_at = db.Column(db.DateTime, nullable=True)
    
    feedbacks = db.relationship("AnswerFeedback", backref="question", lazy=True, cascade="all, delete-orphan")
    notification_logs = db.relationship("EmailNotificationLog", backref="question", lazy=True, cascade="all, delete-orphan", order_by="EmailNotificationLog.created_at.desc()")
    
    def to_dict(self):
        customer = self.customer
        conv = self.conversation
        messages_list = [m.to_dict() for m in conv.messages] if conv else []
        return {
            "id": self.id,
            "shop_id": self.shop_id,
            "customer_id": self.customer_id,
            "customer_name": f"{customer.first_name} {customer.last_name}" if customer else "Unknown",
            "customer_email": customer.email if customer else "N/A",
            "conversation_id": self.conversation_id,
            "question": self.question,
            "ai_answer": self.ai_answer,
            "owner_answer": self.owner_answer,
            "status": self.status,
            "email_status": self.email_status,
            "email_error": self.email_error,
            "email_retries": self.email_retries or 0,
            "email_sent_at": self.email_sent_at.isoformat() if self.email_sent_at else None,
            "email_provider": self.email_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "answered_at": self.answered_at.isoformat() if self.answered_at else None,
            "feedback": [f.to_dict() for f in self.feedbacks],
            "messages": messages_list
        }

class AnswerFeedback(db.Model):
    __tablename__ = "answer_feedback"
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_question_id = db.Column(db.Integer, db.ForeignKey("customer_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_type = db.Column(db.String(10), nullable=False)  # 'good', 'bad'
    reason = db.Column(db.Text, nullable=True)
    correct_answer = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    def to_dict(self):
        q = self.question
        cust = q.customer if q else None
        return {
            "id": self.id,
            "shop_id": self.shop_id,
            "customer_question_id": self.customer_question_id,
            "customer_name": f"{cust.first_name} {cust.last_name}".strip() if cust else "Anonymous",
            "customer_email": cust.email if cust else "N/A",
            "question": q.question if q else "",
            "ai_answer": q.ai_answer if q else "",
            "feedback_type": self.feedback_type,
            "reason": self.reason,
            "correct_answer": self.correct_answer,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class ActivityLog(db.Model):
    __tablename__ = "activity_logs"
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "action": self.action,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class EmailNotificationLog(db.Model):
    __tablename__ = "email_notification_logs"
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_question_id = db.Column(db.Integer, db.ForeignKey("customer_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_email = db.Column(db.String(150), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # 'resend', 'smtp', 'mock'
    status = db.Column(db.String(30), nullable=False)  # 'sent', 'failed'
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "shop_id": self.shop_id,
            "customer_question_id": self.customer_question_id,
            "recipient_email": self.recipient_email,
            "provider": self.provider,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


