from datetime import date
from decimal import Decimal, InvalidOperation

CATEGORIES = ("Food", "Rent", "Shopping", "Bills", "Study", "Travel")
DESCRIPTION_MAX_LENGTH = 200
MAX_AMOUNT_CENTS = 10_000_000_000  # 100,000,000.00


def parse_amount_cents(raw):
    """Return the amount as an integer number of cents, or None if it is invalid.

    Decimal is used instead of float so that values such as 0.1 + 0.2 never
    creep into stored money.
    """
    try:
        amount = Decimal(raw.strip())
    except (InvalidOperation, AttributeError):
        return None

    if not amount.is_finite() or amount <= 0:
        return None

    cents = amount * 100
    if cents != cents.to_integral_value():
        return None  # more than two decimal places

    cents = int(cents)
    if cents > MAX_AMOUNT_CENTS:
        return None
    return cents


def format_cents(cents):
    """Format integer cents for display, for example 1250 -> '12.50'."""
    return f"{cents // 100}.{cents % 100:02d}"


def parse_date(raw):
    """Return the date as YYYY-MM-DD, or None if it is not a valid date."""
    try:
        return date.fromisoformat(raw).isoformat()
    except (ValueError, TypeError):
        return None


def validate_expense(form):
    """Check expense form data.

    Returns (data, errors). data is None when there are errors.
    """
    errors = []

    description = form.get("description", "").strip()
    if not description:
        errors.append("Description is required.")
    elif len(description) > DESCRIPTION_MAX_LENGTH:
        errors.append(f"Description must be {DESCRIPTION_MAX_LENGTH} characters or fewer.")

    amount_cents = parse_amount_cents(form.get("amount", ""))
    if amount_cents is None:
        errors.append("Amount must be a positive number with at most two decimal places.")

    expense_date = parse_date(form.get("date", ""))
    if expense_date is None:
        errors.append("Date is invalid.")

    category = form.get("category", "")
    if category not in CATEGORIES:
        errors.append("Choose a valid category.")

    if errors:
        return None, errors

    data = {
        "description": description,
        "amount_cents": amount_cents,
        "date": expense_date,
        "category": category,
    }
    return data, []
