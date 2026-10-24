import re

import pytest

from expense_tracker import create_app
from tests.conftest import PASSWORD


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


def test_csrf_token_required_when_enabled(tmp_path):
    app = create_app("development", {"DATABASE": str(tmp_path / "csrf.db"), "TESTING": True})
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


def test_production_requires_secret_key(tmp_path, monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        create_app("production", {"DATABASE": str(tmp_path / "prod.db")})


def test_unknown_environment_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Unknown APP_ENV"):
        create_app("staging", {"DATABASE": str(tmp_path / "x.db")})
