import sqlite3

from flask import current_app, g

from expense_tracker.validation import CATEGORIES

# Categories as they were when migration 1 shipped. Migrations must not read
# the live CATEGORIES list, or old migrations would change when it does.
_V1_CATEGORIES = ("Food", "Rent", "Shopping", "Bills", "Study", "Travel")

USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL
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


def _expenses_table_sql(categories):
    category_list = ", ".join(f"'{c}'" for c in categories)
    return f"""
    CREATE TABLE expenses_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
        description TEXT NOT NULL CHECK (length(trim(description)) > 0),
        amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
        category TEXT CHECK (category IS NULL OR category IN ({category_list})),
        date TEXT NOT NULL
    )
    """


def _table_exists(db, name):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone() is not None


def _rebuild_expenses(db, categories, copy_sql=None):
    """Replace the expenses table with one that allows `categories`.

    SQLite cannot change a CHECK constraint in place, so the table is rebuilt:
    create the new table, copy the rows, drop the old table, and rename.
    """
    db.execute(_expenses_table_sql(categories))
    if copy_sql and _table_exists(db, "expenses"):
        db.execute(copy_sql)
        db.execute("DROP TABLE expenses")
    db.execute("ALTER TABLE expenses_new RENAME TO expenses")
    db.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses (user_id, date)")


def _migrate_v1(db):
    """Create the schema. Also converts the early prototype table, which stored
    amounts as floats in `amount`, to integer cents in `amount_cents`."""
    db.execute(USERS_TABLE)

    copy_sql = None
    if _table_exists(db, "expenses"):
        columns = {row["name"] for row in db.execute("PRAGMA table_info(expenses)")}
        category = "category" if "category" in columns else "NULL"
        copy_sql = f"""
            INSERT INTO expenses_new (id, user_id, description, amount_cents, category, date)
            SELECT id, user_id, description, CAST(ROUND(amount * 100) AS INTEGER), {category}, date
            FROM expenses
        """

    _rebuild_expenses(db, _V1_CATEGORIES, copy_sql)


def _migrate_v2(db):
    """Allow every category in CATEGORIES."""
    _rebuild_expenses(
        db,
        CATEGORIES,
        """
        INSERT INTO expenses_new (id, user_id, description, amount_cents, category, date)
        SELECT id, user_id, description, amount_cents, category, date FROM expenses
        """,
    )


def _migrate_v3(db):
    """Add one optional monthly spending limit per user."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS monthly_limits (
            user_id INTEGER PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
            limit_cents INTEGER NOT NULL CHECK (limit_cents > 0)
        )
    """)


def _migrate_v4(db):
    """Add one profile per user: personal details and an optional photo."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
            full_name TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            address TEXT NOT NULL DEFAULT '',
            photo BLOB,
            photo_type TEXT
        )
    """)


# Each entry upgrades the database by one version. Never edit an entry that has
# shipped; add a new one instead.
MIGRATIONS = [_migrate_v1, _migrate_v2, _migrate_v3, _migrate_v4]


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
