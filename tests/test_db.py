import sqlite3
from contextlib import closing

from expense_tracker import create_app
from expense_tracker.db import MIGRATIONS


def _columns(path, table):
    with closing(sqlite3.connect(path)) as con:
        return [row[1] for row in con.execute(f"PRAGMA table_info({table})")]


def _user_version(path):
    with closing(sqlite3.connect(path)) as con:
        return con.execute("PRAGMA user_version").fetchone()[0]


def _create_prototype_database(path):
    """Build the early schema: float amounts and a category column added later."""
    with closing(sqlite3.connect(path)) as con:
        con.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users (id),
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                category TEXT
            );
            INSERT INTO users (username, password_hash) VALUES ('alice', 'x');
            INSERT INTO expenses (user_id, description, amount, date, category)
                VALUES (1, 'Lunch', 12.5, '2026-01-01', 'Food'),
                       (1, 'Old thing', 3.1, '2026-01-02', NULL);
            """
        )


def test_prototype_database_is_migrated(tmp_path):
    path = tmp_path / "old.db"
    _create_prototype_database(path)

    create_app("testing", {"DATABASE": str(path)})

    assert "amount_cents" in _columns(path, "expenses")
    assert "amount" not in _columns(path, "expenses")
    assert _user_version(path) == len(MIGRATIONS)

    with closing(sqlite3.connect(path)) as con:
        rows = con.execute(
            "SELECT description, amount_cents, category FROM expenses ORDER BY id"
        ).fetchall()
    assert rows == [("Lunch", 1250, "Food"), ("Old thing", 310, None)]


def test_migration_is_idempotent(tmp_path):
    path = tmp_path / "test.db"
    create_app("testing", {"DATABASE": str(path)})
    create_app("testing", {"DATABASE": str(path)})
    assert _user_version(path) == len(MIGRATIONS)


def test_fresh_database_has_expected_schema(tmp_path):
    path = tmp_path / "fresh.db"
    create_app("testing", {"DATABASE": str(path)})

    assert _columns(path, "expenses") == [
        "id", "user_id", "description", "amount_cents", "category", "date",
    ]
    with closing(sqlite3.connect(path)) as con:
        indexes = [row[1] for row in con.execute("PRAGMA index_list(expenses)")]
    assert "idx_expenses_user_date" in indexes


def test_database_rejects_invalid_category(tmp_path):
    path = tmp_path / "check.db"
    create_app("testing", {"DATABASE": str(path)})

    with closing(sqlite3.connect(path)) as con:
        con.execute("INSERT INTO users (username, password_hash) VALUES ('alice', 'x')")
        try:
            con.execute(
                "INSERT INTO expenses (user_id, description, amount_cents, category, date) "
                "VALUES (1, 'x', 100, 'Gadgets', '2026-01-01')"
            )
        except sqlite3.IntegrityError:
            rejected = True
        else:
            rejected = False
    assert rejected


def test_database_rejects_non_positive_amount(tmp_path):
    path = tmp_path / "check.db"
    create_app("testing", {"DATABASE": str(path)})

    with closing(sqlite3.connect(path)) as con:
        con.execute("INSERT INTO users (username, password_hash) VALUES ('alice', 'x')")
        try:
            con.execute(
                "INSERT INTO expenses (user_id, description, amount_cents, category, date) "
                "VALUES (1, 'x', 0, 'Food', '2026-01-01')"
            )
        except sqlite3.IntegrityError:
            rejected = True
        else:
            rejected = False
    assert rejected
