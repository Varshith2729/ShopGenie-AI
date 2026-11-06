import pytest
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app import create_app
from backend.app.models import db
from backend.config import TestConfig

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_headers(client):
    """Helper to register and login a test shop owner."""
    res = client.post("/api/auth/register", json={
        "full_name": "Test Owner",
        "email": "owner@test.com",
        "password": "password123",
        "confirm_password": "password123",
        "shop_name": "Test Shop",
        "slug": "test-shop"
    })
    token = res.get_json()["data"]["token"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

