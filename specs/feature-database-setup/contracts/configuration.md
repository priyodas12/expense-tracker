# Contract: configuration

All values come from the environment (or an untracked `.env`). None may be committed or logged.

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `DATABASE_URL` | Yes (all environments) | none | PostgreSQL connection URL, e.g. `postgresql://user:password@host:5432/dbname`. Replaces the old `DATABASE` file path. Startup fails with a redacted error if missing or unreachable. |
| `DATABASE_SCHEMA` | No | `public` | Schema used for the connection's `search_path`. Tests set a unique value per test. |
| `MAINTENANCE_MODE` | No | off | `1`/`true` serves the 503 maintenance page for all non-static requests and skips database start-up. |
| `SECRET_KEY` | Production | none | Unchanged. Must be identical on every server so sessions work across servers. |
| `APP_ENV` | No | `development` | Unchanged. |
| `TEST_DATABASE_URL` | Tests | `postgresql://penny:penny@localhost:5432/penny_test` | Database the test suite uses. |

## Local development database (`compose.yaml`)

- One `postgres` service with a named volume and a health check.
- Creates two databases: `penny_dev` (via `POSTGRES_DB`) and `penny_test` (via `docker/initdb/01-create-test-db.sql`, which runs only when the volume is empty), user `penny`, a development-only password.
- Start: `docker compose up -d`; stop: `docker compose down`; reset: `docker compose down -v`.
- Development-only credentials in `compose.yaml` and `.env.example` are placeholders and not valid for any real deployment.
