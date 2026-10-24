import csv
import io
import math
from datetime import date

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
    Response,
)

from expense_tracker.auth import login_required
from expense_tracker.db import get_db
from expense_tracker.validation import CATEGORIES, format_cents, parse_date, validate_expense

bp = Blueprint("expenses", __name__)

# Characters that make spreadsheet apps treat a cell as a formula.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def read_filters():
    """Read and validate the start, end and category query parameters."""
    filters = {
        "start": request.args.get("start", ""),
        "end": request.args.get("end", ""),
        "category": request.args.get("category", ""),
    }

    start = parse_date(filters["start"]) if filters["start"] else None
    end = parse_date(filters["end"]) if filters["end"] else None
    category = filters["category"] if filters["category"] in CATEGORIES else ""

    if (filters["start"] and start is None) or (filters["end"] and end is None):
        flash("Date filter is invalid.", "error")
        start = end = None
    elif start and end and start > end:
        flash("Start date must be on or before end date.", "error")
        start = end = None

    if filters["category"] and not category:
        flash("Choose a valid category filter.", "error")

    return {"start": start or "", "end": end or "", "category": category}


def build_where(user_id, filters):
    """Return a SQL WHERE clause and its parameters. Only fixed SQL fragments
    are joined into the clause; every user-supplied value is a parameter."""
    clauses = ["user_id = ?"]
    params = [user_id]

    if filters["start"]:
        clauses.append("date >= ?")
        params.append(filters["start"])
    if filters["end"]:
        clauses.append("date <= ?")
        params.append(filters["end"])
    if filters["category"]:
        clauses.append("category = ?")
        params.append(filters["category"])

    return " AND ".join(clauses), params


def csv_safe(value):
    text = str(value)
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


def get_owned_expense(expense_id):
    expense = get_db().execute(
        "SELECT id, description, amount_cents, date, category FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, g.user["id"]),
    ).fetchone()
    if expense is None:
        abort(404)
    return expense


def read_expense_form():
    """Return validated expense data, or None after flashing each error."""
    data, errors = validate_expense(request.form)
    for error in errors:
        flash(error, "error")
    return data


@bp.route("/")
def index():
    if g.user is None:
        return render_template("landing.html")

    filters = read_filters()
    where, params = build_where(g.user["id"], filters)
    db = get_db()

    summary = db.execute(
        f"SELECT COUNT(*) AS count, COALESCE(SUM(amount_cents), 0) AS total FROM expenses WHERE {where}",
        params,
    ).fetchone()

    per_page = current_app.config["PER_PAGE"]
    page_count = max(1, math.ceil(summary["count"] / per_page))
    page = min(max(request.args.get("page", 1, type=int), 1), page_count)

    expenses = db.execute(
        f"""
        SELECT id, description, amount_cents, date, category
        FROM expenses
        WHERE {where}
        ORDER BY date DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, per_page, (page - 1) * per_page],
    ).fetchall()

    return render_template(
        "index.html",
        expenses=expenses,
        total_cents=summary["total"],
        count=summary["count"],
        page=page,
        page_count=page_count,
        today=date.today().isoformat(),
        filters=filters,
        filter_args={key: value for key, value in filters.items() if value},
        categories=CATEGORIES,
    )


@bp.route("/expenses/export.csv")
@login_required
def export():
    filters = read_filters()
    where, params = build_where(g.user["id"], filters)
    rows = get_db().execute(
        f"SELECT date, description, category, amount_cents FROM expenses WHERE {where} ORDER BY date, id",
        params,
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Category", "Amount"])
    for row in rows:
        writer.writerow([
            csv_safe(row["date"]),
            csv_safe(row["description"]),
            csv_safe(row["category"] or ""),
            format_cents(row["amount_cents"]),
        ])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = 'attachment; filename="expenses.csv"'
    return response


@bp.route("/expenses", methods=["POST"])
@login_required
def add():
    data = read_expense_form()
    if data is not None:
        db = get_db()
        db.execute(
            """
            INSERT INTO expenses (user_id, description, amount_cents, date, category)
            VALUES (:user_id, :description, :amount_cents, :date, :category)
            """,
            {**data, "user_id": g.user["id"]},
        )
        db.commit()
        flash("Expense added.", "success")
    return redirect(url_for("expenses.index"))


@bp.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    expense = get_owned_expense(expense_id)

    if request.method == "POST":
        data = read_expense_form()
        if data is not None:
            db = get_db()
            db.execute(
                """
                UPDATE expenses
                SET description = :description, amount_cents = :amount_cents,
                    date = :date, category = :category
                WHERE id = :id AND user_id = :user_id
                """,
                {**data, "id": expense_id, "user_id": g.user["id"]},
            )
            db.commit()
            flash("Expense updated.", "success")
            return redirect(url_for("expenses.index"))

    return render_template("edit.html", expense=expense, categories=CATEGORIES)


@bp.route("/expenses/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete(expense_id):
    get_owned_expense(expense_id)
    db = get_db()
    db.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, g.user["id"]))
    db.commit()
    flash("Expense deleted.", "success")
    return redirect(url_for("expenses.index"))
