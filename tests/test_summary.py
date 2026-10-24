from expense_tracker.validation import CATEGORIES


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


def summary(client, query=""):
    return client.get(f"/expenses/summary.json{query}")


def test_summary_requires_login(client):
    response = summary(client)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_summary_empty(user):
    client = user()
    payload = summary(client).get_json()
    assert payload == {"total_cents": 0, "count": 0, "slices": []}


def test_summary_totals_by_category_in_fixed_slot_order(user):
    client = user()
    add(client, "Lunch", "12.50", "2026-10-01", category="Food")
    add(client, "Dinner", "7.50", "2026-10-02", category="Food")
    add(client, "Flat", "800", "2026-10-01", category="Rent")

    payload = summary(client).get_json()

    assert payload["total_cents"] == 82000
    assert payload["count"] == 3
    assert payload["slices"] == [
        {"name": "Food", "cents": 2000, "count": 2, "slot": 0},
        {"name": "Rent", "cents": 80000, "count": 1, "slot": 1},
    ]


def test_late_categories_keep_their_own_slot(user):
    client = user()
    add(client, "Gift", "20", "2026-10-01", category="Gifts")
    add(client, "Pills", "5", "2026-10-01", category="Health")
    add(client, "Coffee", "3", "2026-10-01", category="Food")

    payload = summary(client).get_json()

    assert payload["total_cents"] == 2800
    assert payload["slices"] == [
        {"name": "Food", "cents": 300, "count": 1, "slot": 0},
        {"name": "Health", "cents": 500, "count": 1, "slot": 7},
        {"name": "Gifts", "cents": 2000, "count": 1, "slot": 9},
    ]


def test_every_category_has_a_slot_in_list_order(user):
    client = user()
    for category in CATEGORIES:
        add(client, category, "1", "2026-10-01", category=category)

    slices = summary(client).get_json()["slices"]

    assert [s["name"] for s in slices] == list(CATEGORIES)
    assert [s["slot"] for s in slices] == list(range(len(CATEGORIES)))


def test_summary_respects_filters(user):
    client = user()
    add(client, "Old lunch", "10", "2026-09-01", category="Food")
    add(client, "New lunch", "20", "2026-10-01", category="Food")
    add(client, "Bus", "5", "2026-10-02", category="Transport")

    payload = summary(client, "?start=2026-10-01&category=Food").get_json()

    assert payload["total_cents"] == 2000
    assert payload["slices"] == [{"name": "Food", "cents": 2000, "count": 1, "slot": 0}]


def test_invalid_filter_does_not_flash(user):
    client = user()
    client.get("/expenses/summary.json?start=not-a-date")
    with client.session_transaction() as session:
        assert "_flashes" not in session


def test_summary_only_counts_own_expenses(user):
    alice = user("alice")
    add(alice, "Alice lunch", "10", "2026-10-01", category="Food")

    bob = user("bob")
    add(bob, "Bob lunch", "99", "2026-10-01", category="Food")

    payload = summary(bob).get_json()
    assert payload["total_cents"] == 9900
    assert payload["slices"] == [{"name": "Food", "cents": 9900, "count": 1, "slot": 0}]


def test_index_renders_chart_card(user):
    client = user()
    response = client.get("/")
    assert b'id="category-chart"' in response.data
    assert b"/expenses/summary.json" in response.data
    assert b"js/category-chart.js" in response.data
