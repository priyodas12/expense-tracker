import csv
import io
import math
from datetime import date, datetime
from xml.sax.saxutils import escape

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from expense_tracker.auth import login_required
from expense_tracker.db import get_db
from expense_tracker.validation import CATEGORIES, format_cents, parse_date, validate_expense

bp = Blueprint("expenses", __name__)

# Characters that make spreadsheet apps treat a cell as a formula.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def read_filters(notify=True):
    """Read and validate the start, end and category query parameters.

    notify=False skips the flash messages, for polling endpoints that would
    otherwise pile messages into the session on every request."""
    filters = {
        "start": request.args.get("start", ""),
        "end": request.args.get("end", ""),
        "category": request.args.get("category", ""),
    }

    start = parse_date(filters["start"]) if filters["start"] else None
    end = parse_date(filters["end"]) if filters["end"] else None
    category = filters["category"] if filters["category"] in CATEGORIES else ""

    if (filters["start"] and start is None) or (filters["end"] and end is None):
        if notify:
            flash("Date filter is invalid.", "error")
        start = end = None
    elif start and end and start > end:
        if notify:
            flash("Start date must be on or before end date.", "error")
        start = end = None

    if filters["category"] and not category and notify:
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


def export_filename(extension):
    """Name exports by when they were made, for example 2026-10-24_10-45-30_expense.pdf."""
    return f"{datetime.now():%Y-%m-%d_%H-%M-%S}_expense.{extension}"


def filter_description(filters):
    dates = "All dates"
    if filters["start"] or filters["end"]:
        dates = f"{filters['start'] or 'the beginning'} to {filters['end'] or 'today'}"
    category = filters["category"] or "All categories"
    return f"{dates}  |  {category}"


def fetch_export_rows(filters):
    where, params = build_where(g.user["id"], filters)
    return get_db().execute(
        f"SELECT date, description, category, amount_cents FROM expenses WHERE {where} ORDER BY date, id",
        params,
    ).fetchall()


def build_pdf(rows, filters):
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=9, leading=11)
    amount_cell = ParagraphStyle("amount_cell", parent=cell, alignment=TA_RIGHT)
    total_cents = sum(row["amount_cents"] for row in rows)

    header = ["Date", "Description", "Category", "Amount"]
    data = [header]
    for row in rows:
        data.append([
            Paragraph(escape(row["date"]), cell),
            Paragraph(escape(row["description"]), cell),
            Paragraph(escape(row["category"] or ""), cell),
            Paragraph(format_cents(row["amount_cents"]), amount_cell),
        ])
    data.append(["", "", Paragraph("<b>Total</b>", cell), Paragraph(f"<b>{format_cents(total_cents)}</b>", amount_cell)])

    table = Table(data, colWidths=[28 * mm, 80 * mm, 34 * mm, 28 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, colors.HexColor("#d9dde3")),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor("#1d1f23")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="Expenses",
        author=current_app.config["APP_NAME"],
    )
    story = [
        Paragraph(f"{escape(current_app.config['APP_NAME'])} expenses", styles["Title"]),
        Paragraph(f"{escape(g.user['username'])}  |  {escape(filter_description(filters))}", styles["Normal"]),
        Spacer(1, 10),
        table,
    ]
    doc.build(story)
    return buffer.getvalue()


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
def export_csv():
    rows = fetch_export_rows(read_filters())

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
    response.headers["Content-Disposition"] = f'attachment; filename="{export_filename("csv")}"'
    return response


@bp.route("/expenses/export.pdf")
@login_required
def export_pdf():
    filters = read_filters()
    rows = fetch_export_rows(filters)

    response = Response(build_pdf(rows, filters), mimetype="application/pdf")
    response.headers["Content-Disposition"] = f'attachment; filename="{export_filename("pdf")}"'
    return response


@bp.route("/expenses/summary.json")
@login_required
def summary_json():
    """Per-category totals for the pie chart, using the same filters as the list.

    Each category keeps its own slot, so its colour is the same in every view.
    Rows with no category (possible only in old data) get a neutral slice."""
    where, params = build_where(g.user["id"], read_filters(notify=False))
    rows = get_db().execute(
        f"""
        SELECT category, SUM(amount_cents) AS cents, COUNT(*) AS count
        FROM expenses
        WHERE {where}
        GROUP BY category
        """,
        params,
    ).fetchall()
    totals = {row["category"]: row for row in rows}

    slices = []
    for slot, name in enumerate(CATEGORIES):
        if name in totals:
            slices.append({"name": name, "cents": totals[name]["cents"], "count": totals[name]["count"], "slot": slot})

    if None in totals:
        slices.append({
            "name": "Uncategorised",
            "cents": totals[None]["cents"],
            "count": totals[None]["count"],
            "slot": None,
        })

    return {
        "total_cents": sum(s["cents"] for s in slices),
        "count": sum(s["count"] for s in slices),
        "slices": slices,
    }


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
