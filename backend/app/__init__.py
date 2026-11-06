from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from backend.config import Config
from backend.app.models import db

migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize Database & Migrations
    db.init_app(app)
    migrate.init_app(app, db)
    
    # CORS setup
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "X-Customer-Session"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )
    
    # Register API Blueprints
    from backend.app.routes.auth import auth_bp
    from backend.app.routes.dashboard import dashboard_bp
    from backend.app.routes.knowledge import knowledge_bp
    from backend.app.routes.shop import shop_bp
    from backend.app.routes.customer import customer_bp
    from backend.app.routes.questions import questions_bp
    from backend.app.routes.feedback import feedback_bp
    from backend.app.routes.email_routes import email_bp
    
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(knowledge_bp, url_prefix="/api/knowledge")
    app.register_blueprint(shop_bp, url_prefix="/api/shop")
    app.register_blueprint(customer_bp, url_prefix="/api/public")
    app.register_blueprint(questions_bp, url_prefix="/api/questions")
    app.register_blueprint(feedback_bp, url_prefix="/api/feedback")
    app.register_blueprint(email_bp, url_prefix="/api/email")
    
    # Health Check
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "Shop FAQ Bot API",
            "version": "1.0.0"
        }), 200
        
    # Global Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"success": False, "message": "The requested API endpoint was not found."}), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({"success": False, "message": "Internal server error. Please try again later."}), 500

    return app

