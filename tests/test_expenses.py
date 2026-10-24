def add(client, description, amount, expense_date, follow=True):
    return client.post(
        "/expenses",
        data={"description": description, "amount": amount, "date": expense_date},
        follow_redirects=follow,
    )


def test_index_requires_login_and_shows_empty_state(user):
    client = user()
    response = client.get("/")
    assert response.status_code == 200
    assert b"No expenses found." in response.data


def test_add_expense(user):
    client = user()
    response = add(client, "Lunch", "12.50", "2026-10-20")
    assert b"Expense added." in response.data
    assert b"Lunch" in response.data
    assert b"12.50" in response.data


def test_add_rejects_invalid_input(user):
    client = user()
    cases = [
        ("  ", "5", "2026-10-20", b"Description is required."),
        ("Bad", "abc", "2026-10-20", b"Amount must be a positive number."),
        ("Bad", "0", "2026-10-20", b"Amount must be a positive number."),
        ("Bad", "-3", "2026-10-20", b"Amount must be a positive number."),
        ("Bad", "nan", "2026-10-20", b"Amount must be a positive number."),
        ("Bad", "inf", "2026-10-20", b"Amount must be a positive number."),
        ("Bad", "5", "not-a-date", b"Date is invalid."),
    ]
    for description, amount, expense_date, message in cases:
        response = add(client, description, amount, expense_date)
        assert message in response.data
    assert b"No expenses found." in client.get("/").data


def test_total_sums_expenses(user):
    client = user()
    add(client, "A", "10", "2026-10-01")
    add(client, "B", "5.25", "2026-10-02")
    assert b"15.25" in client.get("/").data


def test_edit_expense(user):
    client = user()
    add(client, "Coffee", "4", "2026-10-20")
    response = client.post(
        "/expenses/1/edit",
        data={"description": "Tea", "amount": "3", "date": "2026-10-21"},
        follow_redirects=True,
    )
    assert b"Expense updated." in response.data
    assert b"Tea" in response.data
    assert b"Coffee" not in response.data
    assert b"3.00" in response.data


def test_edit_page_shows_current_values(user):
    client = user()
    add(client, "Coffee", "4", "2026-10-20")
    response = client.get("/expenses/1/edit")
    assert response.status_code == 200
    assert b'value="Coffee"' in response.data


def test_edit_rejects_invalid_input_and_keeps_expense(user):
    client = user()
    add(client, "Coffee", "4", "2026-10-20")
    response = client.post(
        "/expenses/1/edit",
        data={"description": "Tea", "amount": "-1", "date": "2026-10-21"},
        follow_redirects=True,
    )
    assert b"Amount must be a positive number." in response.data
    assert b"Coffee" in client.get("/").data


def test_delete_expense(user):
    client = user()
    add(client, "Coffee", "4", "2026-10-20")
    response = client.post("/expenses/1/delete", follow_redirects=True)
    assert b"Expense deleted." in response.data
    assert b"Coffee" not in response.data
    assert b"No expenses found." in response.data


def test_cannot_edit_or_delete_another_users_expense(user, client):
    owner = user("alice")
    add(owner, "Alice rent", "900", "2026-10-01")
    owner.post("/auth/logout")

    other = user("bobby")
    assert other.get("/expenses/1/edit").status_code == 404
    assert other.post(
        "/expenses/1/edit",
        data={"description": "Hacked", "amount": "1", "date": "2026-10-01"},
    ).status_code == 404
    assert other.post("/expenses/1/delete").status_code == 404

    other.post("/auth/logout")
    owner = user("alice")
    assert b"Alice rent" in owner.get("/").data


def test_date_range_filter_is_inclusive(user):
    client = user()
    add(client, "Early", "1", "2026-09-30")
    add(client, "Start", "2", "2026-10-01")
    add(client, "Middle", "3", "2026-10-15")
    add(client, "End", "4", "2026-10-31")
    add(client, "Late", "5", "2026-11-01")

    response = client.get("/?start=2026-10-01&end=2026-10-31")
    assert response.status_code == 200
    for name in [b"Start", b"Middle", b"End"]:
        assert name in response.data
    for name in [b"Early", b"Late"]:
        assert name not in response.data
    assert b"9.00" in response.data  # 2 + 3 + 4


def test_date_range_with_only_start_or_end(user):
    client = user()
    add(client, "Old", "1", "2026-01-01")
    add(client, "New", "2", "2026-06-01")

    assert b"New" in client.get("/?start=2026-03-01").data
    assert b"Old" not in client.get("/?start=2026-03-01").data
    assert b"Old" in client.get("/?end=2026-03-01").data
    assert b"New" not in client.get("/?end=2026-03-01").data


def test_invalid_date_filter_shows_all_expenses(user):
    client = user()
    add(client, "Old", "1", "2026-01-01")
    response = client.get("/?start=bogus&end=2026-12-31")
    assert b"Date filter is invalid." in response.data
    assert b"Old" in response.data


def test_reversed_date_range_is_rejected(user):
    client = user()
    add(client, "Old", "1", "2026-01-01")
    response = client.get("/?start=2026-12-31&end=2026-01-01")
    assert b"Start date must be on or before end date." in response.data
    assert b"Old" in response.data
