from tests.conftest import PASSWORD


def test_register_and_login(client):
    response = client.post(
        "/auth/register",
        data={"username": "alice", "password": PASSWORD},
        follow_redirects=True,
    )
    assert b"Account created. Please log in." in response.data

    response = client.post(
        "/auth/login",
        data={"username": "alice", "password": PASSWORD},
        follow_redirects=True,
    )
    assert b'class="avatar-link"' in response.data


def test_duplicate_username_rejected_case_insensitive(client):
    client.post("/auth/register", data={"username": "alice", "password": PASSWORD})
    response = client.post(
        "/auth/register",
        data={"username": "Alice", "password": PASSWORD},
        follow_redirects=True,
    )
    assert b"Username is already taken." in response.data


def test_short_password_rejected(client):
    response = client.post(
        "/auth/register",
        data={"username": "alice", "password": "short"},
        follow_redirects=True,
    )
    assert b"Password must be at least 8 characters." in response.data


def test_overlong_password_rejected(client):
    response = client.post(
        "/auth/register",
        data={"username": "alice", "password": "x" * 129},
        follow_redirects=True,
    )
    assert b"Password must be 128 characters or fewer." in response.data


def test_short_username_rejected(client):
    response = client.post(
        "/auth/register",
        data={"username": "al", "password": PASSWORD},
        follow_redirects=True,
    )
    assert b"Username must be 3-30 characters" in response.data


def test_username_with_invalid_characters_rejected(client):
    response = client.post(
        "/auth/register",
        data={"username": "<script>", "password": PASSWORD},
        follow_redirects=True,
    )
    assert b"Username must be 3-30 characters" in response.data


def test_wrong_password_rejected(client):
    client.post("/auth/register", data={"username": "alice", "password": PASSWORD})
    response = client.post(
        "/auth/login",
        data={"username": "alice", "password": "wrong-password"},
        follow_redirects=True,
    )
    assert b"Invalid username or password." in response.data
    assert b"Signed in as" not in response.data


def test_anonymous_user_sees_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Penny Trail" in response.data
    assert b"Create an account" in response.data
    assert b"See your dashboard" in response.data


def test_expense_pages_redirect_anonymous_user_to_login(client):
    response = client.get("/expenses/1/edit")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_logout_redirects_to_homepage(user, client):
    user()
    response = client.post("/auth/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_logout_ends_session(user, client):
    user()
    client.post("/auth/logout")
    response = client.get("/")
    assert response.status_code == 200
    assert b"Signed in as" not in response.data
    assert b"Create an account" in response.data


def test_users_only_see_their_own_expenses(user, client):
    user("alice")
    client.post(
        "/expenses",
        data={"description": "Alice rent", "amount": "900", "date": "2026-10-01", "category": "Rent"},
    )
    client.post("/auth/logout")

    user("bobby")
    response = client.get("/")
    assert b"Alice rent" not in response.data
    assert b"No expenses found." in response.data


def test_unknown_username_still_checks_a_password_hash(client, monkeypatch):
    # Without this, logins for unknown usernames return faster and reveal which names exist.
    import expense_tracker.auth as auth

    calls = []
    real_check = auth.check_password_hash
    monkeypatch.setattr(auth, "check_password_hash", lambda h, p: calls.append(h) or real_check(h, p))

    response = client.post("/auth/login", data={"username": "nobody", "password": PASSWORD})

    assert b"Invalid username or password." in response.data
    assert calls == [auth._DUMMY_PASSWORD_HASH]


def test_failed_login_log_escapes_username(client, caplog):
    caplog.set_level("INFO")
    client.post("/auth/login", data={"username": "eve\nINFO forged entry" + "x" * 50, "password": PASSWORD})

    messages = [r.getMessage() for r in caplog.records if "Failed login" in r.getMessage()]
    assert len(messages) == 1
    assert "\n" not in messages[0]
    assert "\\n" in messages[0]
    assert "x" * 50 not in messages[0]
