import csv
import io


def add(client, description, amount, expense_date, category="Food", follow=True):
    return client.post(
        "/expenses",
        data={
            "description": description,
            "amount": amount,
            "date": expense_date,
            "category": category,
        },
        follow_redirects=follow,
    )


def expense_data(description, amount, expense_date, category):
    return {
        "description": description,
        "amount": amount,
        "date": expense_date,
        "category": category,
    }


def test_index_shows_empty_state(user):
    client = user()
    response = client.get("/")
    assert response.status_code == 200
    assert b"No expenses found." in response.data


def test_add_expense(user):
    client = user()
    response = add(client, "Lunch", "12.50", "2026-10-20", category="Food")
    assert b"Expense added." in response.data
    assert b"Lunch" in response.data
    assert b"12.50" in response.data


def test_category_dropdown_lists_all_categories(user):
    client = user()
    response = client.get("/")
    for category in [b"Food", b"Rent", b"Shopping", b"Bills", b"Study", b"Travel"]:
        assert b'<option value="%s">' % category in response.data


def test_list_shows_category(user):
    client = user()
    add(client, "Monthly flat", "800", "2026-10-01", category="Rent")
    assert b"<td>Rent</td>" in client.get("/").data


def test_add_rejects_invalid_category(user):
    client = user()
    response = add(client, "Gadget", "50", "2026-10-20", category="Gadgets")
    assert b"Choose a valid category." in response.data
    assert b"No expenses found." in client.get("/").data


def test_add_rejects_missing_category(user):
    client = user()
    response = client.post(
        "/expenses",
        data={"description": "Gadget", "amount": "50", "date": "2026-10-20"},
        follow_redirects=True,
    )
    assert b"Choose a valid category." in response.data


def test_add_rejects_invalid_input(user):
    client = user()
    amount_error = b"Amount must be a positive number"
    cases = [
        ("  ", "5", "2026-10-20", b"Description is required."),
        ("Bad", "abc", "2026-10-20", amount_error),
        ("Bad", "0", "2026-10-20", amount_error),
        ("Bad", "-3", "2026-10-20", amount_error),
        ("Bad", "nan", "2026-10-20", amount_error),
        ("Bad", "inf", "2026-10-20", amount_error),
        ("Bad", "1.005", "2026-10-20", amount_error),
        ("Bad", "0.001", "2026-10-20", amount_error),
        ("Bad", "5", "not-a-date", b"Date is invalid."),
    ]
    for description, amount, expense_date, message in cases:
        response = add(client, description, amount, expense_date)
        assert message in response.data
    assert b"No expenses found." in client.get("/").data


def test_add_rejects_overlong_description(user):
    client = user()
    response = add(client, "x" * 201, "5", "2026-10-20")
    assert b"Description must be 200 characters or fewer." in response.data


def test_amounts_are_stored_and_summed_exactly(user):
    client = user()
    add(client, "A", "0.10", "2026-10-01")
    add(client, "B", "0.20", "2026-10-02")
    response = client.get("/")
    assert b"0.30" in response.data  # floats would give 0.30000000000000004


def test_total_sums_expenses(user):
    client = user()
    add(client, "A", "10", "2026-10-01")
    add(client, "B", "5.25", "2026-10-02")
    assert b"15.25" in client.get("/").data


def test_edit_expense(user):
    client = user()
    add(client, "Coffee", "4", "2026-10-20", category="Food")
    response = client.post(
        "/expenses/1/edit",
        data=expense_data("Tea", "3", "2026-10-21", "Study"),
        follow_redirects=True,
    )
    assert b"Expense updated." in response.data
    assert b"Tea" in response.data
    assert b"Coffee" not in response.data
    assert b"3.00" in response.data
    assert b"<td>Study</td>" in response.data


def test_edit_page_preselects_values(user):
    client = user()
    add(client, "Coffee", "4.5", "2026-10-20", category="Study")
    response = client.get("/expenses/1/edit")
    assert response.status_code == 200
    assert b'value="Coffee"' in response.data
    assert b'value="4.50"' in response.data
    assert b'value="Study" selected' in response.data


def test_edit_rejects_invalid_input_and_keeps_expense(user):
    client = user()
    add(client, "Coffee", "4", "2026-10-20")
    response = client.post(
        "/expenses/1/edit",
        data=expense_data("Tea", "-1", "2026-10-21", "Food"),
        follow_redirects=True,
    )
    assert b"Amount must be a positive number" in response.data
    assert b"Coffee" in client.get("/").data


def test_delete_expense(user):
    client = user()
    add(client, "Coffee", "4", "2026-10-20")
    response = client.post("/expenses/1/delete", follow_redirects=True)
    assert b"Expense deleted." in response.data
    assert b"Coffee" not in response.data
    assert b"No expenses found." in response.data


def test_cannot_edit_or_delete_another_users_expense(user):
    owner = user("alice")
    add(owner, "Alice rent", "900", "2026-10-01", category="Rent")
    owner.post("/auth/logout")

    other = user("bobby")
    assert other.get("/expenses/1/edit").status_code == 404
    assert other.post(
        "/expenses/1/edit",
        data=expense_data("Hacked", "1", "2026-10-01", "Food"),
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


def test_category_filter(user):
    client = user()
    add(client, "Groceries", "20", "2026-10-01", category="Food")
    add(client, "Flat", "900", "2026-10-01", category="Rent")

    response = client.get("/?category=Rent")
    assert b"Flat" in response.data
    assert b"Groceries" not in response.data


def test_invalid_category_filter_is_ignored(user):
    client = user()
    add(client, "Groceries", "20", "2026-10-01", category="Food")
    response = client.get("/?category=Gadgets")
    assert b"Choose a valid category filter." in response.data
    assert b"Groceries" in response.data


def test_total_respects_filters(user):
    client = user()
    add(client, "Groceries", "20", "2026-10-01", category="Food")
    add(client, "Flat", "900", "2026-10-01", category="Rent")
    response = client.get("/?category=Food")
    assert b"20.00" in response.data
    assert b"920.00" not in response.data


def test_pagination_splits_results(user, app):
    app.config["PER_PAGE"] = 2
    client = user()
    for i in range(5):
        add(client, f"Item{i}", "1", f"2026-10-0{i + 1}")

    first = client.get("/")
    assert b"Page 1 of 3" in first.data
    assert first.data.count(b"<td>Item") == 2

    last = client.get("/?page=3")
    assert b"Page 3 of 3" in last.data
    assert last.data.count(b"<td>Item") == 1


def test_default_page_shows_fifteen_expenses(user):
    client = user()
    for i in range(16):
        add(client, f"Item{i:02d}", "1", f"2026-10-{i + 1:02d}")

    first = client.get("/")
    assert b"Page 1 of 2" in first.data
    assert first.data.count(b"<td>Item") == 15

    second = client.get("/?page=2")
    assert second.data.count(b"<td>Item") == 1


def test_page_number_is_clamped(user, app):
    app.config["PER_PAGE"] = 2
    client = user()
    for i in range(3):
        add(client, f"Item{i}", "1", f"2026-10-0{i + 1}")

    assert b"Page 2 of 2" in client.get("/?page=99").data
    assert b"Page 1 of 2" in client.get("/?page=-4").data
    assert b"Page 1 of 2" in client.get("/?page=abc").data


def test_export_csv(user):
    client = user()
    add(client, "Lunch, with team", "12.5", "2026-10-20", category="Food")
    add(client, "Flat", "900", "2026-10-01", category="Rent")

    response = client.get("/expenses/export.csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]

    rows = list(csv.reader(io.StringIO(response.get_data(as_text=True))))
    assert rows[0] == ["Date", "Description", "Category", "Amount"]
    assert ["2026-10-20", "Lunch, with team", "Food", "12.50"] in rows
    assert ["2026-10-01", "Flat", "Rent", "900.00"] in rows


def test_export_respects_filters(user):
    client = user()
    add(client, "Groceries", "20", "2026-10-01", category="Food")
    add(client, "Flat", "900", "2026-10-01", category="Rent")

    response = client.get("/expenses/export.csv?category=Rent")
    text = response.get_data(as_text=True)
    assert "Flat" in text
    assert "Groceries" not in text


def test_export_neutralises_spreadsheet_formulas(user):
    client = user()
    add(client, "=HYPERLINK(\"http://evil\")", "5", "2026-10-01")

    text = client.get("/expenses/export.csv").get_data(as_text=True)
    assert "'=HYPERLINK" in text
    assert ",=HYPERLINK" not in text


def test_export_requires_login(client):
    response = client.get("/expenses/export.csv")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_export_pdf(user):
    client = user()
    add(client, "Lunch", "12.50", "2026-10-20", category="Food")

    response = client.get("/expenses/export.pdf")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert "attachment" in response.headers["Content-Disposition"]
    assert response.data.startswith(b"%PDF")


def test_export_pdf_respects_filters(user):
    client = user()
    add(client, "Groceries", "20", "2026-10-01", category="Food")
    add(client, "Flat", "900", "2026-10-01", category="Rent")

    filtered = client.get("/expenses/export.pdf?category=Rent")
    everything = client.get("/expenses/export.pdf")
    assert filtered.data.startswith(b"%PDF")
    assert len(filtered.data) != len(everything.data)


def test_export_pdf_requires_login(client):
    response = client.get("/expenses/export.pdf")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_export_links_shown_under_heading(user):
    client = user()
    page = client.get("/").get_data(as_text=True)
    assert "/expenses/export.csv" in page
    assert "/expenses/export.pdf" in page
    assert page.index("Export CSV") < page.index('class="filter-bar"')


def test_new_categories_can_be_added_and_filtered(user):
    client = user()
    add(client, "Doctor", "40", "2026-10-01", category="Health")
    add(client, "Movie", "12", "2026-10-02", category="Entertainment")

    assert b"<td>Health</td>" in client.get("/").data
    response = client.get("/?category=Entertainment")
    assert b"Movie" in response.data
    assert b"Doctor" not in response.data


def test_export_filenames_include_date_and_time(user):
    import re

    client = user()
    stamp = r'filename="\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_expense\.'

    csv_header = client.get("/expenses/export.csv").headers["Content-Disposition"]
    pdf_header = client.get("/expenses/export.pdf").headers["Content-Disposition"]
    assert re.search(stamp + r'csv"', csv_header)
    assert re.search(stamp + r'pdf"', pdf_header)
