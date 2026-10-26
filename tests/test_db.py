import threading

import pytest
from psycopg.errors import CheckViolation, UniqueViolation

from expense_tracker import create_app
from expense_tracker.db import MIGRATIONS
from expense_tracker.validation import CATEGORIES
from tests.conftest import TEST_DATABASE_URL


def _version(db_conn):
    return db_conn.execute("SELECT version FROM schema_version").fetchone()["version"]


def _insert_user(db_conn, username="alice"):
    return db_conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (%s, 'x') RETURNING id",
        (username,),
    ).fetchone()["id"]


def test_fresh_schema_reaches_latest_version(app, db_conn):
    assert _version(db_conn) == len(MIGRATIONS)


def test_migration_is_idempotent(app, pg_schema, db_conn):
    create_app(
        "testing",
        {"DATABASE_URL": TEST_DATABASE_URL, "DATABASE_SCHEMA": pg_schema},
    )
    assert _version(db_conn) == len(MIGRATIONS)


def test_expenses_table_has_expected_columns(app, db_conn):
    columns = [
        row["column_name"]
        for row in db_conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'expenses' AND table_schema = current_schema() "
            "ORDER BY ordinal_position"
        )
    ]
    assert columns == ["id", "user_id", "description", "amount_cents", "category", "date"]


def test_user_expense_index_exists(app, db_conn):
    row = db_conn.execute(
        "SELECT 1 AS found FROM pg_indexes "
        "WHERE tablename = 'expenses' AND indexname = 'idx_expenses_user_date' "
        "AND schemaname = current_schema()"
    ).fetchone()
    assert row is not None


def test_database_rejects_invalid_category(app, db_conn):
    user_id = _insert_user(db_conn)
    with pytest.raises(CheckViolation):
        db_conn.execute(
            "INSERT INTO expenses (user_id, description, amount_cents, category, date) "
            "VALUES (%s, 'x', 100, 'Gadgets', '2026-01-01')",
            (user_id,),
        )


def test_database_rejects_non_positive_amount(app, db_conn):
    user_id = _insert_user(db_conn)
    with pytest.raises(CheckViolation):
        db_conn.execute(
            "INSERT INTO expenses (user_id, description, amount_cents, category, date) "
            "VALUES (%s, 'x', 0, 'Food', '2026-01-01')",
            (user_id,),
        )


def test_database_rejects_blank_description(app, db_conn):
    user_id = _insert_user(db_conn)
    with pytest.raises(CheckViolation):
        db_conn.execute(
            "INSERT INTO expenses (user_id, description, amount_cents, category, date) "
            "VALUES (%s, '   ', 100, 'Food', '2026-01-01')",
            (user_id,),
        )


def test_database_accepts_every_category(app, db_conn):
    user_id = _insert_user(db_conn)
    for category in CATEGORIES:
        db_conn.execute(
            "INSERT INTO expenses (user_id, description, amount_cents, category, date) "
            "VALUES (%s, 'x', 100, %s, '2026-01-01')",
            (user_id, category),
        )
    count = db_conn.execute("SELECT COUNT(*) AS n FROM expenses").fetchone()["n"]
    assert count == len(CATEGORIES)


def test_username_uniqueness_ignores_case(app, db_conn):
    _insert_user(db_conn, "alice")
    with pytest.raises(UniqueViolation):
        _insert_user(db_conn, "ALICE")


def test_deleting_user_cascades_to_owned_rows(app, db_conn):
    user_id = _insert_user(db_conn)
    db_conn.execute(
        "INSERT INTO expenses (user_id, description, amount_cents, category, date) "
        "VALUES (%s, 'x', 100, 'Food', '2026-01-01')",
        (user_id,),
    )
    db_conn.execute("INSERT INTO monthly_limits (user_id, limit_cents) VALUES (%s, 5000)", (user_id,))
    db_conn.execute("INSERT INTO profiles (user_id) VALUES (%s)", (user_id,))

    db_conn.execute("DELETE FROM users WHERE id = %s", (user_id,))

    for table in ("expenses", "monthly_limits", "profiles"):
        remaining = db_conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        assert remaining == 0, table


def test_concurrent_startup_applies_migrations_once(pg_schema, db_conn):
    """Several workers starting together must not race on the schema."""
    barrier = threading.Barrier(4)
    errors = []

    def start():
        try:
            barrier.wait()
            create_app(
                "testing",
                {"DATABASE_URL": TEST_DATABASE_URL, "DATABASE_SCHEMA": pg_schema},
            )
        except Exception as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=start) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert _version(db_conn) == len(MIGRATIONS)
    rows = db_conn.execute("SELECT COUNT(*) AS n FROM schema_version").fetchone()["n"]
    assert rows == 1
