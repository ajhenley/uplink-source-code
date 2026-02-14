"""Flask application factory."""
import os
from flask import Flask
from .extensions import db, migrate, socketio, login_manager


def create_app():
    app = Flask(__name__,
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'),
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

    app.config.from_object('app.config.Config')

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="eventlet")
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.game import game_bp
    from .routes.api import api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(game_bp, url_prefix="/game")
    app.register_blueprint(api_bp, url_prefix="/api")

    # Register WebSocket handlers
    from .ws import handlers  # noqa: F401

    # Import models so Alembic can see them
    from .models import (  # noqa: F401
        user_account, game_session, player, gateway, computer,
        vlocation, company, person, mission, connection,
        data_file, access_log, security, message, running_task,
        scheduled_event, bank_account, stock_market, news,
    )

    # Create tables if not using migrations
    with app.app_context():
        db.create_all()

    return app
