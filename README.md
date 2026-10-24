# Penny Trail

Penny Trail is an expense tracker built with Flask. Record what you spend, categorise it, correct mistakes, and see totals for any date range.

## Features

- **Accounts:** register, log in and log out. Passwords are hashed with Werkzeug.
- **Private data:** each user sees and changes only their own expenses.
- **Expenses:** add, edit and delete entries with a description, amount, date and category.
- **Categories:** Food, Rent, Shopping, Bills, Study, Travel, Transport, Health, Entertainment, Gifts, Personal and Other.
- **Filters:** narrow the list by date range (either end optional) and by category. The total follows the filter.
- **Pagination:** long lists are split into pages.
- **CSV export:** download the current filtered list as a spreadsheet. Cells that could run as formulas are neutralised.
- **Money handling:** amounts are stored as integer cents, so totals are exact.
- **Security:** CSRF protection on every form, security headers, hardened session cookies, and generic error pages.

## Requirements

- Python 3.14 (any recent Python 3 should work)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit it
```

## Configuration

Settings come from environment variables, or from a `.env` file in the project root. See `.env.example`.

| Variable     | Default                      | Purpose                                                                 |
|--------------|------------------------------|-------------------------------------------------------------------------|
| `APP_ENV`    | `development`                | `development`, `testing` or `production`. Production enables secure cookies. |
| `SECRET_KEY` | `dev-secret-change-me` (development only) | Signs sessions and CSRF tokens. **Required in production.** |
| `DATABASE`   | `expenses.db` in project root | Path to the SQLite database file.                                      |

Generate a strong key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Running locally

```bash
python app.py
```

Open http://127.0.0.1:5000. This uses Flask's development server with debug mode on, so don't use it in production.

## Running in production

Set the environment, then start Gunicorn:

```bash
APP_ENV=production SECRET_KEY=<your-key> gunicorn -w 4 -b 0.0.0.0:8000 "app:app"
```

Put a reverse proxy such as Nginx or Caddy in front of Gunicorn to terminate HTTPS. Production sets the session cookie to `Secure`, so logins only work over HTTPS. Gunicorn does not run on Windows; use WSL or a Linux host.

## Running the tests

```bash
pytest
```

The suite covers accounts, expense CRUD, validation, filters, pagination, CSV export, database migrations and security headers.

## Database

The database schema is versioned with SQLite's `PRAGMA user_version`. On startup the app applies any pending migrations, each in its own transaction. To change the schema, add a function to `MIGRATIONS` in `expense_tracker/db.py`. Don't edit a migration that has already shipped.

Back up `expenses.db` before upgrading a database that holds real data.

## Project structure

```
expense-tracker/
├── app.py                  # entry point (also used by Gunicorn as app:app)
├── config.py               # configuration classes per environment
├── .env.example            # template for environment settings
├── requirements.txt        # pinned dependencies
├── pytest.ini
├── expense_tracker/
│   ├── __init__.py         # create_app() factory, security headers, error pages
│   ├── auth.py             # register, login, logout, login_required
│   ├── db.py               # SQLite connection and migrations
│   ├── routes.py           # list, filter, export, add, edit and delete expenses
│   ├── validation.py       # input rules, categories, money parsing and formatting
│   ├── templates/          # HTML pages (Jinja2)
│   └── static/style.css    # light and dark theme
└── tests/
    ├── conftest.py         # shared fixtures
    ├── test_auth.py
    ├── test_db.py          # migrations and schema
    ├── test_expenses.py
    └── test_security.py    # CSRF, headers, configuration checks
```

## Pages and routes

| Method(s)  | Path                         | Description                                                                 |
|------------|------------------------------|-----------------------------------------------------------------------------|
| GET        | `/`                          | Landing page, or your expenses when logged in. Query parameters: `start`, `end` (YYYY-MM-DD), `category`, `page`. |
| GET        | `/expenses/export.csv`       | Download expenses as CSV. Accepts the same filters as `/`.                  |
| POST       | `/expenses`                  | Add an expense.                                                             |
| GET, POST  | `/expenses/<id>/edit`        | Show or save an edit form.                                                  |
| POST       | `/expenses/<id>/delete`      | Delete an expense.                                                          |
| GET, POST  | `/auth/register`             | Create an account.                                                          |
| GET, POST  | `/auth/login`                | Log in.                                                                     |
| POST       | `/auth/logout`               | Log out.                                                                    |

Expense routes require a logged-in user. Requests for another user's expense return 404.

## Validation rules

- **Amount:** a positive number with at most two decimal places, up to 100,000,000.00.
- **Date:** a valid `YYYY-MM-DD` date.
- **Description:** required, up to 200 characters.
- **Category:** one of the twelve listed under Features.
- **Username:** 3–30 characters, letters, numbers, dots, dashes and underscores. Not case-sensitive.
- **Password:** 8–128 characters.

## Known limitations

- Login attempts are logged but not rate-limited. For internet-facing use, add rate limiting at the reverse proxy or with an extension such as Flask-Limiter.
- Expenses saved before categories existed have no category. Choose one the next time you edit them.
- SQLite handles a single server well. For several servers writing at once, move to PostgreSQL.
