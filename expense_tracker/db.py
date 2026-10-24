import sqlite3

from flask import current_app, g

from expense_tracker.validation import CATEGORIES

_CATEGORY_LIST = ", ".join(f"'{c}'" for c in CATEGORIES)

USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL
)
"""

# The current expenses table. Migrations below build this shape, so the
# name used here is temporary during a rebuild.
EXPENSES_TABLE = f"""
CREATE TABLE expenses_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    description TEXT NOT NULL CHECK (length(trim(description)) > 0),
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    category TEXT CHECK (category IS NULL OR category IN ({_CATEGORY_LIST})),
    date TEXT NOT NULL
)
"""


def get_db():
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        g.db = db
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _migrate_v1(db):
    """Create the schema. Also converts the early prototype table, which stored
    amounts as floats in `amount`, to integer cents in `amount_cents`."""
    db.execute(USERS_TABLE)
    db.execute(EXPENSES_TABLE)

    legacy = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'expenses'"
    ).fetchone()
    if legacy:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(expenses)")}
        category = "category" if "category" in columns else "NULL"
        db.execute(
            f"""
            INSERT INTO expenses_new (id, user_id, description, amount_cents, category, date)
            SELECT id, user_id, description, CAST(ROUND(amount * 100) AS INTEGER), {category}, date
            FROM expenses
            """
        )
        db.execute("DROP TABLE expenses")

    db.execute("ALTER TABLE expenses_new RENAME TO expenses")
    db.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses (user_id, date)")


# Each entry upgrades the database by one version. Never edit an entry that has
# shipped; add a new one instead.
MIGRATIONS = [_migrate_v1]


def init_db():
    db = get_db()
    current = db.execute("PRAGMA user_version").fetchone()[0]

    for version, migrate in enumerate(MIGRATIONS, start=1):
        if current < version:
            _apply(db, version, migrate)


def _apply(db, version, migrate):
    """Run one migration inside a transaction, so a failure leaves the database unchanged."""
    db.execute("BEGIN")
    try:
        migrate(db)
        db.execute(f"PRAGMA user_version = {int(version)}")
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
