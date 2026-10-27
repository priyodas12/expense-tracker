import logging
import os
from datetime import date

from flask import Flask, render_template, request
from flask_wtf import CSRFProtect

from config import CONFIGS
from expense_tracker.auth import bp as auth_bp
from expense_tracker.db import close_db, init_db
from expense_tracker.pages import bp as pages_bp
from expense_tracker.profile import PHOTO_UPLOAD_LIMIT, avatar_context
from expense_tracker.profile import bp as profile_bp
from expense_tracker.routes import bp as expenses_bp
from expense_tracker.sqlite_import import sqlite_import_cli
from expense_tracker.validation import format_cents

csrf = CSRFProtect()


def create_app(config_name=None, overrides=None):
    """Build the Flask app.

    config_name: "development", "testing" or "production". Defaults to the
    APP_ENV environment variable, then "production", so a server started without
    APP_ENV never runs with debug on or insecure cookies.
    overrides: a dict of config values applied last, mainly for tests.
    """
    config_name = config_name or os.environ.get("APP_ENV", "production")
    if config_name not in CONFIGS:
        raise ValueError(f"Unknown APP_ENV {config_name!r}. Use one of: {', '.join(CONFIGS)}.")

    app = Flask(__name__)
    app.config.from_object(CONFIGS[config_name])
    if overrides:
        app.config.update(overrides)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY is not set. Add it to your environment or .env file.")
    if not app.config["DATABASE_URL"]:
        raise RuntimeError("DATABASE_URL is not set. Add it to your environment or .env file.")

    app.logger.setLevel(logging.INFO)

    @app.before_request
    def serve_maintenance_page():
        # While the database is being moved, answer every request with 503 and
        # touch nothing. Registered before any blueprint, so no user lookup runs.
        if app.config["MAINTENANCE_MODE"] and request.endpoint != "static":
            return render_template("maintenance.html"), 503, {"Retry-After": "3600"}

    @app.before_request
    def allow_photo_upload_size():
        # Every other request keeps the 16 KB MAX_CONTENT_LENGTH. This must be
        # registered before CSRF protection, which reads the form body.
        if request.endpoint == "profile.upload_photo":
            request.max_content_length = PHOTO_UPLOAD_LIMIT

    csrf.init_app(app)
    app.teardown_appcontext(close_db)
    app.add_template_filter(format_cents, "money")
    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(profile_bp)
    app.cli.add_command(sqlite_import_cli)

    @app.context_processor
    def inject_current_year():
        return {"current_year": date.today().year}

    @app.context_processor
    def inject_avatar():
        return {"avatar": avatar_context()}

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; form-action 'self'; frame-ancestors 'none'",
        )
        return response

    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def too_large(error):
        return render_template("413.html"), 413

    @app.errorhandler(500)
    def server_error(error):
        app.logger.error("Unhandled server error: %s", error)
        return render_template("500.html"), 500

    if not app.config["MAINTENANCE_MODE"]:
        with app.app_context():
            init_db()

    return app
