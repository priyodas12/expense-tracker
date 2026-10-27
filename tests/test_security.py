import re

import pytest

from expense_tracker import create_app
from tests.conftest import PASSWORD, TEST_DATABASE_URL


def test_security_headers_present(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_not_found_uses_app_page(user):
    client = user()
    response = client.get("/expenses/999/edit")
    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_csrf_token_required_when_enabled(pg_schema):
    app = create_app(
        "development",
        {
            "DATABASE_URL": TEST_DATABASE_URL,
            "DATABASE_SCHEMA": pg_schema,
            "SECRET_KEY": "csrf-test-key",
            "TESTING": True,
        },
    )
    client = app.test_client()

    response = client.post("/auth/register", data={"username": "alice", "password": PASSWORD})
    assert response.status_code == 400

    page = client.get("/auth/register").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

    response = client.post(
        "/auth/register",
        data={"username": "alice", "password": PASSWORD, "csrf_token": token},
    )
    assert response.status_code == 302


def test_production_requires_secret_key(pg_schema, monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        create_app(
            "production",
            {"DATABASE_URL": TEST_DATABASE_URL, "DATABASE_SCHEMA": pg_schema, "SECRET_KEY": None},
        )


def test_missing_database_url_is_rejected(pg_schema, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        create_app("testing", {"DATABASE_URL": None, "DATABASE_SCHEMA": pg_schema})


def test_unreachable_database_error_does_not_leak_password():
    url = "postgresql://penny:s3cret-pass@127.0.0.1:1/penny_test"
    with pytest.raises(RuntimeError) as excinfo:
        create_app("testing", {"DATABASE_URL": url, "DATABASE_SCHEMA": "public"})
    message = str(excinfo.value)
    assert "penny_test" in message
    assert "s3cret-pass" not in message
    assert "127.0.0.1" in message


def test_unknown_environment_is_rejected(pg_schema):
    with pytest.raises(ValueError, match="Unknown APP_ENV"):
        create_app("staging", {"DATABASE_URL": TEST_DATABASE_URL, "DATABASE_SCHEMA": pg_schema})


def test_unset_app_env_defaults_to_production(pg_schema, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    app = create_app(
        None, {"DATABASE_URL": TEST_DATABASE_URL, "DATABASE_SCHEMA": pg_schema, "SECRET_KEY": "prod-test-key"}
    )
    assert app.config["DEBUG"] is False
    assert app.config["SESSION_COOKIE_SECURE"] is True


def test_development_has_no_fixed_secret_key():
    from config import DevelopmentConfig

    # The key must come from the environment, never from a value written in the code.
    assert "SECRET_KEY" not in vars(DevelopmentConfig)
