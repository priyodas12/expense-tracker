from expense_tracker.routes import month_span


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


def monthly(client, query=""):
    return client.get(f"/expenses/monthly.json{query}")


def test_monthly_requires_login(client):
    response = monthly(client)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_monthly_empty(user):
    client = user()
    payload = monthly(client).get_json()
    assert payload == {"total_cents": 0, "count": 0, "months": []}


def test_monthly_totals_per_month(user):
    client = user()
    add(client, "Lunch", "12.50", "2026-10-01")
    add(client, "Dinner", "7.50", "2026-10-30")
    add(client, "Rent", "800", "2026-09-01", category="Rent")

    payload = monthly(client).get_json()

    assert payload["total_cents"] == 82000
    assert payload["count"] == 3
    assert payload["months"] == [
        {"month": "2026-09", "cents": 80000, "count": 1},
        {"month": "2026-10", "cents": 2000, "count": 2},
    ]


def test_monthly_fills_gaps_with_zero(user):
    client = user()
    add(client, "Old", "5", "2026-01-15")
    add(client, "New", "9", "2026-04-02")

    months = monthly(client).get_json()["months"]

    assert [m["month"] for m in months] == ["2026-01", "2026-02", "2026-03", "2026-04"]
    assert [m["cents"] for m in months] == [500, 0, 0, 900]
    assert [m["count"] for m in months] == [1, 0, 0, 1]


def test_monthly_respects_category_filter(user):
    client = user()
    add(client, "Lunch", "10", "2026-10-01", category="Food")
    add(client, "Flat", "800", "2026-10-01", category="Rent")

    payload = monthly(client, "?category=Food").get_json()

    assert payload["total_cents"] == 1000
    assert payload["months"] == [{"month": "2026-10", "cents": 1000, "count": 1}]


def test_monthly_respects_date_range(user):
    client = user()
    add(client, "Jan", "10", "2026-01-10")
    add(client, "Mar", "20", "2026-03-10")

    payload = monthly(client, "?start=2026-02-01&end=2026-03-31").get_json()

    assert payload["months"] == [{"month": "2026-03", "cents": 2000, "count": 1}]
    assert payload["total_cents"] == 2000


def test_month_span_crosses_year_boundary():
    assert list(month_span("2025-11", "2026-02")) == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_month_span_single_month():
    assert list(month_span("2026-10", "2026-10")) == ["2026-10"]
