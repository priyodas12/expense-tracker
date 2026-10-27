# Penny Trail

Penny Trail is an expense tracker built with Flask. Record what you spend, categorise it, correct mistakes, see totals for any date range, and keep an eye on a monthly spending limit.

## Features

- **Accounts:** register, log in and log out. Passwords are hashed with Werkzeug. When you are logged in, the Log out button sits under your avatar in the top-right corner. Logged-out visitors see Log in and Register in the header instead.
- **Profile:** a round avatar at the top right of every page links to your profile. There you can upload a photo (JPEG, PNG, GIF or WebP, up to 2 MB, or remove it) and add your name, email, contact number and address. All details are optional. Without a photo the avatar shows your initial, taken from your name or username.
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
- PostgreSQL 17 for the database. For development and tests, Docker Compose starts one for you (see below).
- Docker with the Compose plugin, for the local development database

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit it
docker compose up -d            # local PostgreSQL for development and tests
```

`docker compose up -d` starts PostgreSQL with a development user (`penny`) and two databases: `penny_dev` for the app and `penny_test` for the tests. The credentials are development-only placeholders. Stop it with `docker compose down`, or remove its data with `docker compose down -v`.

## Configuration

Settings come from environment variables, or from a `.env` file in the project root. See `.env.example`.

| Variable           | Default                      | Purpose                                                                 |
|--------------------|------------------------------|-------------------------------------------------------------------------|
| `APP_ENV`          | `production` (`development` for `python app.py`) | `development`, `testing` or `production`. Production enables secure cookies and keeps debug off. |
| `SECRET_KEY`       | none (**required**)          | Signs sessions and CSRF tokens. Required in every environment except testing. Must be identical on every server. |
| `DATABASE_URL`     | none (**required**)          | PostgreSQL connection URL, e.g. `postgresql://user:password@host:5432/dbname`. |
| `DATABASE_SCHEMA`  | `public`                     | Schema the connection uses. The tests set a separate schema per test.    |
| `MAINTENANCE_MODE` | off                          | `1` shows the maintenance page (HTTP 503) for every request and skips database start-up. Used during cutover. |
| `TEST_DATABASE_URL`| `postgresql://penny:penny@localhost:5432/penny_test` | Database the test suite uses.                       |

Other settings live in `config.py`. The page size is `PER_PAGE` (15), and the app name shown in headers, titles and the footer is `APP_NAME` ("Penny Trail").

Generate a strong key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Running locally

```bash
python app.py
```

Open http://127.0.0.1:5000. This uses Flask's development server with debug mode on, so don't use it in production. Running `app.py` directly defaults `APP_ENV` to `development`; other entry points (Gunicorn, `flask --app app ...`) default to `production`, so set `APP_ENV=development` in `.env` for local `flask` commands. `SECRET_KEY` must be set in `.env` (see above).

## Running in production

Set the environment, then start Gunicorn:

```bash
APP_ENV=production SECRET_KEY=<your-key> gunicorn -w 4 -b 0.0.0.0:8000 "app:app"
```

Put a reverse proxy such as Nginx or Caddy in front of Gunicorn to terminate HTTPS. Production sets the session cookie to `Secure`, so logins only work over HTTPS. Gunicorn does not run on Windows; use WSL or a Linux host.

### Running more than one server

Several Gunicorn workers or app servers can share one PostgreSQL database. Give every server the same `DATABASE_URL` and the same `SECRET_KEY`, because sessions are signed with that key and must be accepted by every server. Migrations run safely at start-up, because the start-up code holds an advisory lock. Writes are single statements, so each save is either kept or not, with no partial data. If two people edit the same expense at the same moment, the last save wins.

## Running the tests

Start the local database first (`docker compose up -d`), then:

```bash
pytest
```

The suite runs against PostgreSQL. If the database is unreachable, the whole suite is skipped with a message telling you how to start it.

The suite covers accounts, the profile and photo uploads, expense CRUD, validation, filters, sorting, pagination, the category and monthly charts, the monthly spend limit, CSV and PDF export, the policy pages, database migrations, concurrent start-up, two servers sharing one database, the SQLite migration and verification commands, the maintenance page and security headers.

## Database

The app uses PostgreSQL, accessed with `psycopg` and plain SQL (no ORM). The schema version is recorded in a `schema_version` table. On startup the app applies any pending migrations under a database-wide advisory lock, so several servers or workers starting together apply each migration once. Each migration runs in its own transaction. To change the schema, add a function to `MIGRATIONS` in `expense_tracker/db.py`. Don't edit a migration that has already shipped.

Current migrations:

1. Baseline schema: users, expenses (integer cents, categories), monthly limits and profiles (with photo as `bytea`). Equal to the SQLite schema version 4 that the app used before.

### Moving from SQLite

The old single-file SQLite database is moved in a one-time operation. The source is opened read-only and is never changed, and the target must be empty:

```bash
flask --app app sqlite-import migrate --source /path/to/expenses.db
flask --app app sqlite-import verify  --source /path/to/expenses.db
```

`verify` compares row counts, per-user totals in cents, profile photos and password hashes, and changes nothing. The full procedure, including backup, maintenance mode, the smoke check and rollback, is in [docs/cutover.md](docs/cutover.md). The SQLite schema history (versions 1 to 4) is kept in git history and under the `sqlite-final` tag.

## Project structure

```
expense-tracker/
├── app.py                  # entry point (also used by Gunicorn as app:app)
├── config.py               # configuration classes per environment, page size, app name
├── compose.yaml           # local PostgreSQL for development and tests
├── docker/initdb/         # creates the penny_test database on first start
├── docs/cutover.md         # SQLite to PostgreSQL cutover and rollback runbook
├── .env.example            # template for environment settings
├── requirements.txt        # pinned dependencies
├── pytest.ini
├── expense_tracker/
│   ├── __init__.py         # create_app() factory, security headers, error pages, maintenance mode
│   ├── auth.py             # register, login, logout, login_required
│   ├── db.py               # PostgreSQL connection, schema_version, migrations
│   ├── pages.py            # Terms & Conditions and Privacy Policy pages
│   ├── profile.py          # profile details, avatar, photo upload and validation of images
│   ├── routes.py           # list, sort, filter, charts, exports, expenses, monthly limit
│   ├── sqlite_import.py    # one-time migrate and verify commands from the old SQLite file
│   ├── validation.py       # input rules, categories, money parsing and formatting
│   ├── templates/          # HTML pages (Jinja2), including base.html with the footer and maintenance.html
│   └── static/
│       ├── style.css       # styles for the app (light theme only)
│       └── js/
│           ├── category-chart.js   # pie chart and legend
│           ├── monthly-chart.js    # monthly spending bars
│           └── flash.js            # dismissible flash messages
└── tests/
    ├── conftest.py         # shared fixtures: a PostgreSQL schema per test
    ├── test_auth.py
    ├── test_budget.py      # monthly spend limit
    ├── test_concurrency.py # two servers sharing one database
    ├── test_db.py          # migrations, constraints and schema
    ├── test_expenses.py
    ├── test_maintenance.py # maintenance page and 503 responses
    ├── test_monthly.py     # monthly spending endpoint
    ├── test_pages.py       # footer and policy pages
    ├── test_postgres_behaviour.py  # JSON integers, case rules, sorting
    ├── test_profile.py     # profile details, avatar and photo uploads
    ├── test_security.py    # CSRF, headers, configuration checks
    ├── test_sorting.py     # column sorting
    ├── test_sqlite_import.py  # migrate and verify commands
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
- The app is fully offline during the one-time move from SQLite. There is no read-only mode while the data is copied.
- Rolling back to SQLite is possible only during the verification window before the app reopens. Changes saved on PostgreSQL after that cannot be carried back.
