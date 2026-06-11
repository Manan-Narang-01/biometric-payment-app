"""BioPay Flask Frontend Application."""
import os
from flask import Flask
from app.config import Config
from app.blueprints.auth import auth_bp
from app.blueprints.dashboard import dashboard_bp
from app.blueprints.payment import payment_bp
from app.blueprints.profile import profile_bp


def create_app(config=None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(profile_bp)

    # Inject global template variables
    @app.context_processor
    def inject_globals():
        return {"app_name": "BioPay", "app_version": "1.0.0"}

    return app


app = create_app()
