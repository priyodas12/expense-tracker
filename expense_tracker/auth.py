import functools
import re

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from psycopg.errors import UniqueViolation

from expense_tracker.db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
PASSWORD_MIN = 8
PASSWORD_MAX = 128  # long enough for passphrases, short enough to keep hashing cheap


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            "SELECT id, username FROM users WHERE id = %s", (user_id,)
        ).fetchone()


def login_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped


def validate_credentials(username, password):
    """Return an error message, or None if the username and password are acceptable."""
    if not USERNAME_PATTERN.match(username):
        return "Username must be 3-30 characters: letters, numbers, dots, dashes or underscores."
    if len(password) < PASSWORD_MIN:
        return f"Password must be at least {PASSWORD_MIN} characters."
    if len(password) > PASSWORD_MAX:
        return f"Password must be {PASSWORD_MAX} characters or fewer."
    return None


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = validate_credentials(username, password)

        if error is None:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
            except UniqueViolation:
                db.rollback()
                error = "Username is already taken."
            else:
                current_app.logger.info("Registered user %s", username)
                flash("Account created. Please log in.", "success")
                return redirect(url_for("auth.login"))

        flash(error, "error")

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT id, password_hash FROM users WHERE lower(username) = lower(%s)", (username,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            # Log the attempt without the password.
            current_app.logger.info("Failed login attempt for username %s", username)
            flash("Invalid username or password.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("expenses.index"))

    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("expenses.index"))
