import math
from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from expense_tracker.auth import login_required
from expense_tracker.db import get_db

bp = Blueprint("expenses", __name__)


def parse_amount(raw):
    try:
        amount = float(raw)
    except ValueError:
        return None
    if not math.isfinite(amount) or amount <= 0:
        return None
    return amount


def parse_date(raw):
    """Return the date as YYYY-MM-DD, or None if it is not a valid date."""
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        return None


def read_expense_form():
    """Return (description, amount, date) from the form, or None after flashing an error."""
    description = request.form.get("description", "").strip()
    amount = parse_amount(request.form.get("amount", ""))
    expense_date = parse_date(request.form.get("date", ""))

    if not description:
        flash("Description is required.")
    elif amount is None:
        flash("Amount must be a positive number.")
    elif expense_date is None:
        flash("Date is invalid.")
    else:
        return description, amount, expense_date
    return None


def get_owned_expense(expense_id):
    expense = get_db().execute(
        "SELECT id, description, amount, date FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, g.user["id"]),
    ).fetchone()
    if expense is None:
        abort(404)
    return expense


@bp.route("/")
def index():
    if g.user is None:
        return render_template("landing.html")

    start = request.args.get("start", "")
    end = request.args.get("end", "")
    start_date = parse_date(start) if start else None
    end_date = parse_date(end) if end else None

    if (start and start_date is None) or (end and end_date is None):
        flash("Date filter is invalid.")
        start_date = end_date = None
    elif start_date and end_date and start_date > end_date:
        flash("Start date must be on or before end date.")
        start_date = end_date = None

    sql = "SELECT id, description, amount, date FROM expenses WHERE user_id = ?"
    params = [g.user["id"]]
    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)
    sql += " ORDER BY date DESC, id DESC"

    expenses = get_db().execute(sql, params).fetchall()
    total = sum(row["amount"] for row in expenses)

    return render_template(
        "index.html",
        expenses=expenses,
        total=total,
        today=date.today().isoformat(),
        start=start_date or "",
        end=end_date or "",
    )


@bp.route("/expenses", methods=["POST"])
@login_required
def add():
    fields = read_expense_form()
    if fields is not None:
        db = get_db()
        db.execute(
            "INSERT INTO expenses (user_id, description, amount, date) VALUES (?, ?, ?, ?)",
            (g.user["id"], *fields),
        )
        db.commit()
        flash("Expense added.")
    return redirect(url_for("expenses.index"))


@bp.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    expense = get_owned_expense(expense_id)

    if request.method == "POST":
        fields = read_expense_form()
        if fields is not None:
            db = get_db()
            db.execute(
                "UPDATE expenses SET description = ?, amount = ?, date = ? WHERE id = ? AND user_id = ?",
                (*fields, expense_id, g.user["id"]),
            )
            db.commit()
            flash("Expense updated.")
            return redirect(url_for("expenses.index"))

    return render_template("edit.html", expense=expense)


@bp.route("/expenses/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete(expense_id):
    get_owned_expense(expense_id)
    db = get_db()
    db.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, g.user["id"]))
    db.commit()
    flash("Expense deleted.")
    return redirect(url_for("expenses.index"))
