import functools
import sqlite3

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from expense_tracker.db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")

USERNAME_MIN = 3
USERNAME_MAX = 30
PASSWORD_MIN = 8


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            "SELECT id, username FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def login_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = None

        if not USERNAME_MIN <= len(username) <= USERNAME_MAX:
            error = f"Username must be {USERNAME_MIN}-{USERNAME_MAX} characters."
        elif len(password) < PASSWORD_MIN:
            error = f"Password must be at least {PASSWORD_MIN} characters."
        else:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
            except sqlite3.IntegrityError:
                error = "Username is already taken."

        if error is None:
            flash("Account created. Please log in.")
            return redirect(url_for("auth.login"))
        flash(error)

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT id, password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.")
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("expenses.index"))

    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
