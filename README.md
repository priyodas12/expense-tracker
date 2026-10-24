# Penny Trail

Penny Trail is a simple expense tracker built with Flask. Record what you spend, correct mistakes, and see your totals for any date range.

## Features

- **Accounts:** register, log in and log out. Passwords are stored as hashes.
- **Private data:** each user sees and changes only their own expenses.
- **Add, edit and delete** expenses (description, amount and date).
- **Date range filter:** show expenses between two dates. Either end can be left empty, and the total updates to match.
- **Landing page:** visitors see a short description of the app with sample data.

## Requirements

- Python 3.14 (any recent Python 3 should work)

## Setup

Clone the project and create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Settings are read from environment variables. You can also put them in a `.env` file in the project root:

| Variable     | Default                  | Purpose                                      |
|--------------|--------------------------|----------------------------------------------|
| `SECRET_KEY` | `dev-secret-change-me`   | Signs login sessions. Set your own before deploying. |
| `DATABASE`   | `expenses.db` (project root) | Path to the SQLite database file.        |

Example `.env`:

```
SECRET_KEY=replace-with-a-long-random-string
```

## Running the app

```bash
python app.py
```

Then open http://127.0.0.1:5000 in your browser. The database file is created automatically on first run.

This starts Flask's development server with debug mode on. It is not suitable for production.

## Running the tests

```bash
pytest
```

## Project structure

```
expense-tracker/
├── app.py                  # entry point
├── config.py               # settings (app name, secret key, database path)
├── requirements.txt        # pinned dependencies
├── pytest.ini
├── expense_tracker/
│   ├── __init__.py         # create_app() application factory
│   ├── auth.py             # register, login, logout, login_required
│   ├── db.py               # SQLite connection and schema
│   ├── routes.py           # home page, add, edit and delete expenses
│   ├── templates/          # HTML pages (Jinja2)
│   └── static/style.css    # light and dark theme
└── tests/
    ├── conftest.py         # shared fixtures
    ├── test_auth.py
    └── test_expenses.py
```

## Pages and routes

| Method(s)      | Path                              | Description                          |
|----------------|-----------------------------------|--------------------------------------|
| GET            | `/`                               | Landing page, or your expenses when logged in. Accepts `start` and `end` query parameters (YYYY-MM-DD). |
| POST           | `/expenses`                       | Add an expense.                      |
| GET, POST      | `/expenses/<id>/edit`             | Show or save an edit form.           |
| POST           | `/expenses/<id>/delete`           | Delete an expense.                   |
| GET, POST      | `/auth/register`                  | Create an account.                   |
| GET, POST      | `/auth/login`                     | Log in.                              |
| POST           | `/auth/logout`                    | Log out.                             |

Expense routes require a logged-in user. Requests for another user's expense return 404.

## Notes

- Amounts must be positive numbers. Dates must be valid `YYYY-MM-DD` values.
- Usernames are 3–30 characters and are not case-sensitive. Passwords must be at least 8 characters.
- The database schema is created automatically when the app starts. The app has no migration tool yet, so an existing database from an older version needs to be moved or deleted.
