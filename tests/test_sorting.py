import re


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


def descriptions_in_order(response):
    """Return the Description cell text of each row, in the order shown."""
    rows = re.findall(rb'<td>([^<]*)</td>\s*<td>[^<]*</td>\s*<td class="num">', response.data)
    return [row.decode() for row in rows]


def seed(client):
    add(client, "banana", "30", "2026-10-02", category="Food")
    add(client, "Apple", "5", "2026-10-03", category="Bills")
    add(client, "cherry", "12.50", "2026-10-01", category="Travel")


def test_default_order_is_newest_date_first(user):
    client = user()
    seed(client)
    assert descriptions_in_order(client.get("/")) == ["Apple", "banana", "cherry"]


def test_sort_by_amount_ascending(user):
    client = user()
    seed(client)
    response = client.get("/?sort=amount&dir=asc")
    assert descriptions_in_order(response) == ["Apple", "cherry", "banana"]


def test_sort_by_amount_descending(user):
    client = user()
    seed(client)
    response = client.get("/?sort=amount&dir=desc")
    assert descriptions_in_order(response) == ["banana", "cherry", "Apple"]


def test_sort_by_description_ignores_case(user):
    client = user()
    seed(client)
    response = client.get("/?sort=description&dir=asc")
    assert descriptions_in_order(response) == ["Apple", "banana", "cherry"]


def test_sort_by_category_ascending(user):
    client = user()
    seed(client)
    response = client.get("/?sort=category&dir=asc")
    assert descriptions_in_order(response) == ["Apple", "banana", "cherry"]


def test_sort_by_date_ascending(user):
    client = user()
    seed(client)
    response = client.get("/?sort=date&dir=asc")
    assert descriptions_in_order(response) == ["cherry", "banana", "Apple"]


def test_unknown_sort_column_falls_back_to_date(user):
    client = user()
    seed(client)
    response = client.get("/?sort=id;DROP&dir=asc")
    assert response.status_code == 200
    # The column falls back to date; the valid direction is still honoured.
    assert descriptions_in_order(response) == ["cherry", "banana", "Apple"]


def test_unknown_direction_falls_back_to_desc(user):
    client = user()
    seed(client)
    response = client.get("/?sort=amount&dir=sideways")
    assert descriptions_in_order(response) == ["banana", "cherry", "Apple"]


def test_header_links_flip_direction_for_active_column(user):
    client = user()
    seed(client)
    response = client.get("/?sort=amount&dir=asc")
    assert b'sort=amount&amp;dir=desc' in response.data
    assert b'sort=date&amp;dir=asc' in response.data
    assert b'aria-sort="ascending"' in response.data


def test_sort_persists_through_pagination(user, app):
    app.config["PER_PAGE"] = 2
    client = user()
    seed(client)

    response = client.get("/?sort=amount&dir=asc&page=1")
    next_link = re.search(rb'href="([^"]*page=2[^"]*)"', response.data)
    assert next_link is not None
    assert b"sort=amount" in next_link.group(1)
    assert b"dir=asc" in next_link.group(1)


def test_header_click_resets_page_and_keeps_filters(user, app):
    app.config["PER_PAGE"] = 2
    client = user()
    seed(client)

    response = client.get("/?page=2&category=Food")
    header = re.search(rb'href="([^"]*sort=amount[^"]*)"', response.data)
    assert header is not None
    assert b"page=" not in header.group(1)
    assert b"category=Food" in header.group(1)
