from flask import Flask

from config import Config
from expense_tracker.auth import bp as auth_bp
from expense_tracker.db import close_db, init_db
from expense_tracker.routes import bp


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    app.teardown_appcontext(close_db)
    app.register_blueprint(auth_bp)
    app.register_blueprint(bp)

    with app.app_context():
        init_db()

    return app
