import logging
import os

from flask import Flask, render_template
from flask_wtf import CSRFProtect

from config import CONFIGS
from expense_tracker.auth import bp as auth_bp
from expense_tracker.db import close_db, init_db
from expense_tracker.routes import bp as expenses_bp
from expense_tracker.validation import format_cents

csrf = CSRFProtect()


def create_app(config_name=None, overrides=None):
    """Build the Flask app.

    config_name: "development", "testing" or "production". Defaults to the
    APP_ENV environment variable, then "development".
    overrides: a dict of config values applied last, mainly for tests.
    """
    config_name = config_name or os.environ.get("APP_ENV", "development")
    if config_name not in CONFIGS:
        raise ValueError(f"Unknown APP_ENV {config_name!r}. Use one of: {', '.join(CONFIGS)}.")

    app = Flask(__name__)
    app.config.from_object(CONFIGS[config_name])
    if overrides:
        app.config.update(overrides)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY is not set. Add it to your environment or .env file.")

    app.logger.setLevel(logging.INFO)

    csrf.init_app(app)
    app.teardown_appcontext(close_db)
    app.add_template_filter(format_cents, "money")
    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; img-src 'self' data:; "
            "form-action 'self'; frame-ancestors 'none'",
        )
        return response

    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        app.logger.error("Unhandled server error: %s", error)
        return render_template("500.html"), 500

    with app.app_context():
        init_db()

    return app
