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
        except Exception as e:
            print(f"Migration note: {e}")
            
        print("Database tables and email tracking schema verified.")

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    print(f"Starting Shop FAQ Bot Backend on http://0.0.0.0:{port} (debug={debug})")
    app.run(host="0.0.0.0", port=port, debug=debug)

