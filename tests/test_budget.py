from datetime import date

from tests.conftest import PASSWORD


def this_month():
    return date.today().strftime("%Y-%m")


def add(client, description, amount, expense_date, category="Food"):
    client.post(
        "/expenses",
        data={
            "description": description,
            "amount": amount,
            "date": expense_date,
            "category": category,
        },
    )


def set_limit(client, amount):
    return client.post("/budget", data={"limit": amount}, follow_redirects=True)


def test_budget_requires_login(client):
    response = client.post("/budget", data={"limit": "500"})
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_no_limit_prompts_user(user):
    client = user()
    response = client.get("/")
    assert b"No limit set" in response.data
    assert b"Set limit" in response.data


def test_set_limit_shows_spent_and_left(user):
    client = user()
    set_limit(client, "500")
    add(client, "Groceries", "120.50", f"{this_month()}-03")

    response = client.get("/")

    assert b"Spent <strong>120.50</strong> of 500.00" in response.data
    assert b"<strong>379.50 left</strong>" in response.data
    assert b'aria-valuenow="24.1"' in response.data


def test_over_limit_shows_amount_over(user):
    client = user()
    set_limit(client, "100")
    add(client, "Flight", "150", f"{this_month()}-10", category="Travel")

    response = client.get("/")

    assert b"<strong class=\"over\">50.00 over limit</strong>" in response.data
    assert b'class="limit-fill over"' in response.data
    assert b'style="width: 100%"' in response.data


def test_only_current_month_counts(user):
    client = user()
    set_limit(client, "300")
    add(client, "Last month", "200", "2000-01-05")
    add(client, "This month", "50", f"{this_month()}-01")

    response = client.get("/")

    assert b"Spent <strong>50.00</strong> of 300.00" in response.data


def test_budget_ignores_list_filters(user):
    client = user()
    set_limit(client, "300")
    add(client, "Coffee", "20", f"{this_month()}-02", category="Food")
    add(client, "Rent", "200", f"{this_month()}-02", category="Rent")

    response = client.get("/?category=Food")

    assert b"Spent <strong>220.00</strong> of 300.00" in response.data


def test_invalid_limit_is_rejected_and_keeps_existing(user):
    client = user()
    set_limit(client, "400")

    response = set_limit(client, "abc")

    assert b"Monthly limit must be a positive amount" in response.data
    assert b"of 400.00" in client.get("/").data


def test_zero_and_too_many_decimals_rejected(user):
    client = user()
    assert b"Monthly limit must be a positive amount" in set_limit(client, "0").data
    assert b"Monthly limit must be a positive amount" in set_limit(client, "10.555").data
    assert b"No limit set" in client.get("/").data


def test_updating_limit_replaces_it(user):
    client = user()
    set_limit(client, "400")
    set_limit(client, "650.25")

    response = client.get("/")

    assert b"of 650.25" in response.data
    assert b"Update limit" in response.data


def test_remove_limit(user):
    client = user()
    set_limit(client, "400")

    response = client.post("/budget/delete", follow_redirects=True)

    assert b"Monthly limit removed." in response.data
    assert b"No limit set" in client.get("/").data


def test_limits_are_private_per_user(user):
    client = user("alice")
    set_limit(client, "900")

    other = user("bob")
    response = other.get("/")

    assert b"No limit set" in response.data
    assert b"of 900.00" not in response.data
