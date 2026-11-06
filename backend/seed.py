import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app import create_app
from backend.app.models import db, User, Shop, KnowledgeBase, ActivityLog
from backend.app.utils.security import hash_password

def seed_demo_data():
    app = create_app()
    with app.app_context():
        print("Cleaning and seeding demo shops...")
        db.create_all()
        
        # Check if already seeded
        if User.query.filter_by(email="ravi@gmail.com").first():
            print("Demo accounts already exist. Skipping seed.")
            return

        # -------------------------------------------------------------
        # SHOP A: Ravi Mobiles
        # -------------------------------------------------------------
        user_a = User(
            full_name="Ravi Kumar",
            email="ravi@gmail.com",
            password_hash=hash_password("password123")
        )
        db.session.add(user_a)
        db.session.flush()

        shop_a = Shop(
            owner_id=user_a.id,
            shop_name="Ravi Mobiles",
            slug="ravi-mobiles",
            description="Premium smartphone retailer and repair center in town."
        )
        db.session.add(shop_a)
        db.session.flush()

        kb_a1 = KnowledgeBase(
            shop_id=shop_a.id,
            title="Shop Timings",
            content="Our shop opens at 9 AM and closes at 9 PM. We are open Monday to Saturday. Sunday is a holiday.",
            category="Timings",
            source_type="manual"
        )
        kb_a2 = KnowledgeBase(
            shop_id=shop_a.id,
            title="Products and Brands",
            content="We sell Samsung, Apple, Vivo, Oppo, and OnePlus smartphones and official accessories.",
            category="Products",
            source_type="manual"
        )
        kb_a3 = KnowledgeBase(
            shop_id=shop_a.id,
            title="Return Policy",
            content="Customers can return unused products within 7 days. Original bills and intact boxes are mandatory.",
            category="Policy",
            source_type="manual"
        )
        db.session.add_all([kb_a1, kb_a2, kb_a3])

        # -------------------------------------------------------------
        # SHOP B: Sri Fashion
        # -------------------------------------------------------------
        user_b = User(
            full_name="Sri Devi",
            email="sri@gmail.com",
            password_hash=hash_password("password123")
        )
        db.session.add(user_b)
        db.session.flush()

        shop_b = Shop(
            owner_id=user_b.id,
            shop_name="Sri Fashion",
            slug="sri-fashion",
            description="Curated collection of men's and women's contemporary and ethnic wear."
        )
        db.session.add(shop_b)
        db.session.flush()

        kb_b1 = KnowledgeBase(
            shop_id=shop_b.id,
            title="Opening Hours",
            content="Our shop opens at 10 AM and closes at 8 PM. We are open all 7 days of the week.",
            category="Timings",
            source_type="manual"
        )
        kb_b2 = KnowledgeBase(
            shop_id=shop_b.id,
            title="Clothing Collection",
            content="We sell men's and women's clothing, ethnic wear, sarees, kurtas, formal shirts, and modern fashion wear.",
            category="Products",
            source_type="manual"
        )
        kb_b3 = KnowledgeBase(
            shop_id=shop_b.id,
            title="Exchange and Return Policy",
            content="Customers can exchange or return products within 5 days with tags intact.",
            category="Policy",
            source_type="manual"
        )
        db.session.add_all([kb_b1, kb_b2, kb_b3])

        db.session.commit()
        print("Demo data seeded successfully!")
        print("Shop A: Ravi Mobiles -> http://localhost:5173/s/ravi-mobiles (Email: ravi@gmail.com / password123)")
        print("Shop B: Sri Fashion -> http://localhost:5173/s/sri-fashion (Email: sri@gmail.com / password123)")

if __name__ == "__main__":
    seed_demo_data()

