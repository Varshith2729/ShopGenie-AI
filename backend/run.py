import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app import create_app
from backend.app.models import db
from sqlalchemy import inspect, text

app = create_app()

def init_db():
    with app.app_context():
        # Ensure tables are created
        db.create_all()
        
        # Check and migrate columns on customer_questions if using existing db
        try:
            inspector = inspect(db.engine)
            if "customer_questions" in inspector.get_table_names():
                existing_cols = [c["name"] for c in inspector.get_columns("customer_questions")]
                with db.engine.connect() as conn:
                    if "email_error" not in existing_cols:
                        conn.execute(text("ALTER TABLE customer_questions ADD COLUMN email_error TEXT"))
                    if "email_retries" not in existing_cols:
                        conn.execute(text("ALTER TABLE customer_questions ADD COLUMN email_retries INTEGER DEFAULT 0"))
                    if "email_sent_at" not in existing_cols:
                        conn.execute(text("ALTER TABLE customer_questions ADD COLUMN email_sent_at TIMESTAMP"))
                    if "email_provider" not in existing_cols:
                        conn.execute(text("ALTER TABLE customer_questions ADD COLUMN email_provider VARCHAR(50)"))
                    conn.commit()

            # Check and migrate columns on answer_feedback if using existing db
            if "answer_feedback" in inspector.get_table_names():
                fb_cols = [c["name"] for c in inspector.get_columns("answer_feedback")]
                with db.engine.connect() as conn:
                    if "rating" not in fb_cols:
                        conn.execute(text("ALTER TABLE answer_feedback ADD COLUMN rating INTEGER"))
                    if "target_type" not in fb_cols:
                        conn.execute(text("ALTER TABLE answer_feedback ADD COLUMN target_type VARCHAR(20) DEFAULT 'ai_answer'"))
                    if "message_id" not in fb_cols:
                        conn.execute(text("ALTER TABLE answer_feedback ADD COLUMN message_id INTEGER"))
                    conn.execute(text("UPDATE answer_feedback SET target_type = 'ai_answer' WHERE target_type IS NULL"))
                    conn.commit()
        except Exception as e:
            print(f"Migration note: {e}")
            
        print("Database tables, email tracking schema, and feedback schema verified.")

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    print(f"Starting ShopGenie AI Backend on http://0.0.0.0:{port} (debug={debug})")
    app.run(host="0.0.0.0", port=port, debug=debug)

