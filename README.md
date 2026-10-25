# Penny Trail

Penny Trail is an expense tracker built with Flask. Record what you spend, categorise it, correct mistakes, see totals for any date range, and keep an eye on a monthly spending limit.

## Features

- **Accounts:** register, log in and log out. Passwords are hashed with Werkzeug.
- **Profile:** a round avatar at the top right of every page links to your profile. There you can upload a photo (JPEG, PNG, GIF or WebP, up to 2 MB, or remove it) and add your name, email, contact number and address. Without a photo the avatar shows your initial.
- **Private data:** each user sees and changes only their own expenses.
- **Expenses:** add, edit and delete entries with a description, amount, date and category.
- **Categories:** Food, Rent, Shopping, Bills, Study, Travel, Transport, Health, Entertainment, Gifts, Personal and Other.
- **Filters:** narrow the list by date range (either end optional) and by category. The total follows the filter.
- **Sorting:** click a column header (date, description, category or amount) to sort ascending or descending. Sorting applies across all pages and keeps your filters.
- **Pagination:** the list shows 15 expenses per page, with Previous and Next links that keep your filters and sort order.
- **Monthly spend limit:** set one limit for the calendar month. A horizontal bar shows how much you have spent and how much is left, and turns red with the amount over once you go past it. Remove it at any time.
- **Spending by category:** a pie chart of the current filter, with a legend showing each category's total and share. It refreshes automatically.
- **Monthly spending:** a bar chart of total spending per month, with months that had no expenses shown as empty bars. It follows the same filters as the list.
- **Exports:** download the current filtered list as CSV or PDF. CSV cells that could run as formulas are neutralised.
- **Money handling:** amounts are stored as integer cents, so totals are exact.
- **Policy pages:** Terms & Conditions and Privacy Policy, linked from a footer on every page. The copyright year updates automatically.
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

Other settings live in `config.py`. The page size is `PER_PAGE` (15), and the app name shown in headers, titles and the footer is `APP_NAME` ("Penny Trail").

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

The suite covers accounts, the profile and photo uploads, expense CRUD, validation, filters, sorting, pagination, the category and monthly charts, the monthly spend limit, CSV and PDF export, the policy pages, database migrations and security headers.

## Database

The database schema is versioned with SQLite's `PRAGMA user_version`. On startup the app applies any pending migrations, each in its own transaction. To change the schema, add a function to `MIGRATIONS` in `expense_tracker/db.py`. Don't edit a migration that has already shipped.

Current migrations:

1. Users and expenses (converting the early float-based prototype to integer cents).
2. Allow every category in the current list.
3. Monthly spending limits, one optional row per user.
4. Profiles: personal details and an optional photo, one row per user.

Back up `expenses.db` before upgrading a database that holds real data.

## Project structure

```
expense-tracker/
├── app.py                  # entry point (also used by Gunicorn as app:app)
├── config.py               # configuration classes per environment, page size, app name
├── .env.example            # template for environment settings
├── requirements.txt        # pinned dependencies
├── pytest.ini
├── expense_tracker/
│   ├── __init__.py         # create_app() factory, security headers, error pages, footer year
│   ├── auth.py             # register, login, logout, login_required
│   ├── db.py               # SQLite connection and migrations
│   ├── pages.py            # Terms & Conditions and Privacy Policy pages
│   ├── profile.py          # profile details, avatar, photo upload and validation of images
│   ├── routes.py           # list, sort, filter, charts, exports, expenses, monthly limit
│   ├── validation.py       # input rules, categories, money parsing and formatting
│   ├── templates/          # HTML pages (Jinja2), including base.html with the footer
│   └── static/
│       ├── style.css       # styles for the app (light theme only)
│       └── js/
│           ├── category-chart.js   # pie chart and legend
│           ├── monthly-chart.js    # monthly spending bars
│           └── flash.js            # dismissible flash messages
└── tests/
    ├── conftest.py         # shared fixtures
    ├── test_auth.py
    ├── test_budget.py      # monthly spend limit
    ├── test_db.py          # migrations and schema
    ├── test_expenses.py
    ├── test_monthly.py     # monthly spending endpoint
    ├── test_pages.py       # footer and policy pages
    ├── test_profile.py     # profile details, avatar and photo uploads
    ├── test_security.py    # CSRF, headers, configuration checks
    ├── test_sorting.py     # column sorting
    └── test_summary.py     # category summary endpoint
```

## Pages and routes

| Method(s)  | Path                         | Description                                                                 |
|------------|------------------------------|-----------------------------------------------------------------------------|
| GET        | `/`                          | Landing page, or your expenses when logged in. Query parameters: `start`, `end` (YYYY-MM-DD), `category`, `sort` (`date`, `description`, `category` or `amount`), `dir` (`asc` or `desc`), `page`. |
| GET        | `/expenses/export.csv`       | Download expenses as CSV. Accepts the same filters as `/`.                  |
| GET        | `/expenses/export.pdf`       | Download expenses as a PDF. Accepts the same filters as `/`.                |
| GET        | `/expenses/summary.json`     | Category totals for the pie chart. Accepts the same filters as `/`.         |
| GET        | `/expenses/monthly.json`     | Monthly totals for the bar chart. Accepts the same filters as `/`.          |
| POST       | `/expenses`                  | Add an expense.                                                             |
| GET, POST  | `/expenses/<id>/edit`        | Show or save an edit form.                                                  |
| POST       | `/expenses/<id>/delete`      | Delete an expense.                                                          |
| POST       | `/budget`                    | Set or update this month's spending limit.                                  |
| POST       | `/budget/delete`             | Remove the spending limit.                                                  |
| GET, POST  | `/profile`                   | Show or save your name, email, contact number and address.                  |
| GET        | `/profile/photo`             | Your profile photo. Returns 404 if none is set.                             |
| POST       | `/profile/photo/upload`      | Upload a profile photo (up to 2 MB).                                        |
| POST       | `/profile/photo/remove`      | Remove your profile photo.                                                  |
| GET        | `/terms-and-conditions`      | Terms & Conditions.                                                         |
| GET        | `/privacy-policy`            | Privacy Policy.                                                             |
| GET, POST  | `/auth/register`             | Create an account.                                                          |
| GET, POST  | `/auth/login`                | Log in.                                                                     |
| POST       | `/auth/logout`               | Log out.                                                                    |

Expense, chart, export, budget and profile routes require a logged-in user. Requests for another user's expense return 404. Each user's spending limit and profile, including the photo, is private to them.

Profile photos are stored in the database, not on disk, so backups of `expenses.db` include them. Uploads are checked by their file signature, not their filename, so only real JPEG, PNG, GIF and WebP images are accepted. The upload route accepts bodies up to 2 MB plus a small allowance for the form envelope. Every other route keeps the 16 KB request limit.

## Validation rules

- **Amount:** a positive number with at most two decimal places, up to 100,000,000.00. The monthly limit uses the same rule.
- **Profile:** all fields optional. Name up to 100 characters, email a valid address up to 254 characters, contact number 20 characters or fewer with at least 7 digits (digits, spaces, `+`, `-` and brackets only), address up to 300 characters.
- **Date:** a valid `YYYY-MM-DD` date.
- **Description:** required, up to 200 characters.
- **Category:** one of the twelve listed under Features.
- **Username:** 3–30 characters, letters, numbers, dots, dashes and underscores. Not case-sensitive.
- **Password:** 8–128 characters.

## Known limitations

- Login attempts are logged but not rate-limited. For internet-facing use, add rate limiting at the reverse proxy or with an extension such as Flask-Limiter.
- Expenses saved before categories existed have no category. Choose one the next time you edit them.
- The monthly spending limit is a single amount that applies to every month. It is not set per month.
- The monthly limit card updates when the page reloads, not in the background as the pie chart does.
- The Terms & Conditions and Privacy Policy pages contain dummy operator details and example commitments. Replace them with your real details and have them reviewed before going live.
- There is no self-service account deletion yet. The privacy policy directs users to email for deletion requests.
- SQLite handles a single server well. For several servers writing at once, move to PostgreSQL.
