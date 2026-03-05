from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_cors import CORS
import os

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()  # No cors here; set during init_app


def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)

    # Load configuration
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    if config_name == 'production':
        app.config.from_object('config.ProductionConfig')
        # Validate required production settings
        if not app.config.get('DATABASE_URL'):
            raise ValueError("DATABASE_URL environment variable must be set in production")
        if not app.config.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY environment variable must be set in production")
        cors_origins = app.config.get('CORS_ORIGINS', [])
        if not cors_origins or cors_origins == ['']:
            raise ValueError("CORS_ORIGINS must be set in production")
    elif config_name == 'testing':
        app.config.from_object('config.TestingConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # CORS -- use config-driven origins instead of wildcard
    allowed_origins = app.config.get('CORS_ORIGINS', ['http://localhost:3000'])
    socketio.init_app(app, cors_allowed_origins=allowed_origins)
    CORS(app, supports_credentials=True, origins=allowed_origins)

    # Set db in models after initialization
    from app import models
    models.db = db

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Import models after db is set
    from app.models import Worker

    @login_manager.user_loader
    def load_user(user_id):
        """Load user for Flask-Login"""
        return Worker.query.get(int(user_id))

    # Register blueprints
    from app.routes import auth, tickets, messages, workers, chats, agent
    app.register_blueprint(auth.bp)
    app.register_blueprint(tickets.bp)
    app.register_blueprint(messages.bp)
    app.register_blueprint(workers.bp)
    app.register_blueprint(chats.bp)
    app.register_blueprint(agent.bp)
    
    # Register optional blueprints if they exist
    try:
        from app.routes.admin_config import bp as admin_config_bp
        app.register_blueprint(admin_config_bp)
    except ImportError:
        pass
    try:
        from app.routes.admin_sync import bp as admin_sync_bp
        app.register_blueprint(admin_sync_bp)
    except ImportError:
        pass
    
    try:
        from app.routes.mfa import bp as mfa_bp
        app.register_blueprint(mfa_bp)
    except ImportError:
        pass

    # Import socketio handlers
    from app import socketio_handlers

    # Setup logging
    from app.logging_config import setup_logging
    setup_logging(app)

    # Security headers -- applied to every response
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '0'  # Disabled in favor of CSP
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' ws://localhost:5000 wss://localhost:5000; "
            "frame-ancestors 'none';"
        )
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # Create database tables and seed default channels (Get-Help, General)
    with app.app_context():
        db.create_all()
        try:
            from app.services.seed_channels import seed_default_channels
            seed_default_channels()
        except Exception as e:
            if app.debug:
                import logging
                logging.getLogger(__name__).warning("Seed default channels failed: %s", e)
            # Non-fatal: channels may already exist or DB not ready

    return app
