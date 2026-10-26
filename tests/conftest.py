import os
import uuid

import psycopg
import pytest
from psycopg.rows import dict_row

from expense_tracker import create_app

PASSWORD = "password123"

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://penny:penny@localhost:5432/penny_test",
)


@pytest.fixture(scope="session", autouse=True)
def require_postgres():
    """Skip the whole suite, with a clear message, when the test database is not running."""
    try:
        with psycopg.connect(TEST_DATABASE_URL, connect_timeout=3):
            pass
    except psycopg.OperationalError:
        pytest.skip(
            "PostgreSQL test database is unreachable. Start it with `docker compose up -d` "
            "or set TEST_DATABASE_URL."
        )


@pytest.fixture
def pg_schema():
    """A fresh PostgreSQL schema for one test, dropped afterwards."""
    schema = f"test_{uuid.uuid4().hex}"
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute(f"CREATE SCHEMA {schema}")
    yield schema
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA {schema} CASCADE")


@pytest.fixture
def db_conn(pg_schema):
    """A direct connection to the test schema, for inspecting rows and schema."""
    with psycopg.connect(
        TEST_DATABASE_URL,
        row_factory=dict_row,
        options=f"-c search_path={pg_schema}",
    ) as conn:
        yield conn


@pytest.fixture
def app(pg_schema):
    return create_app(
        "testing",
        {"DATABASE_URL": TEST_DATABASE_URL, "DATABASE_SCHEMA": pg_schema},
    )


@pytest.fixture
def user(client):
    """Register and log in a user, returning the client for that user."""

    def _sign_in(username="alice", password=PASSWORD):
        client.post("/auth/register", data={"username": username, "password": password})
        client.post("/auth/login", data={"username": username, "password": password})
        return client

    return _sign_in
