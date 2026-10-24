import pytest

from expense_tracker import create_app

PASSWORD = "password123"


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture
def user(client):
    """Register and log in a user, returning the client for that user."""

    def _sign_in(username="alice", password=PASSWORD):
        client.post("/auth/register", data={"username": username, "password": password})
        client.post("/auth/login", data={"username": username, "password": password})
        return client

    return _sign_in
