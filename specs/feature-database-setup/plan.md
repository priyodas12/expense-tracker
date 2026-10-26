# Implementation Plan: Database Migration to PostgreSQL

**Branch**: `feature/database-setup` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/feature-database-setup/spec.md`

## Summary

Replace the single-file SQLite database with PostgreSQL as the only supported database, so several
app servers can write at once. The app keeps its plain-SQL style (no ORM) and moves from `sqlite3`
to `psycopg` 3. A one-time Flask CLI command copies an existing SQLite database into an empty
PostgreSQL database in one transaction and a second command verifies the result. Local development
and tests run against a Docker Compose PostgreSQL. The app gets a maintenance-mode switch for the
offline cutover, and a runbook documents backup, migrate, verify, switch-over, and rollback within
a verification window. User-facing behaviour, URLs and templates do not change.

## Technical Context

**Language/Version**: Python 3.14 (target), Flask 3.1

**Primary Dependencies**: Flask, Flask-WTF, Werkzeug, Gunicorn, ReportLab (unchanged); adds `psycopg[binary]==3.3.6` (new, see research R1; a `cp314` manylinux wheel is published for this version).

**Storage**: PostgreSQL (one database, one schema). SQLite is read only by the migration command.

**Testing**: pytest + pytest-flask against a Docker PostgreSQL, one throwaway schema per test.

**Target Platform**: Linux server, Gunicorn behind Nginx/Caddy; PostgreSQL managed by the operator.

**Project Type**: Web application (server-rendered Flask monolith).

**Performance Goals**: List and chart pages under 2 s for a user with 10,000 expenses (SC-005).

**Constraints**: Integer cents only; parameterised SQL; CSP unchanged; no inline scripts or styles; credentials only via environment configuration and never logged (FR-012); 16 KB / 2 MB request limits unchanged.

**Scale/Scope**: Under 100 users and 100,000 expenses in total; photos up to 2 MB each stored in the database.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / constraint | Status | Notes |
|---|---|---|
| I. Money is integer cents | Pass | `amount_cents` / `limit_cents` stay `bigint`/`integer`; migration copies values verbatim and verification compares sums in cents. |
| II. Single filter pipeline | Pass | `read_filters()`, `build_where()`, `get_owned_expense()` keep their roles; only placeholder style and a few SQL functions change. |
| III. Migrations append-only | Pass (2.0.0) | PostgreSQL chain starts from a baseline `_migrate_v1` equal to SQLite v4, as constitution 2.0.0 allows. Append-only from then on. |
| IV. Test-backed changes | Pass | Full suite runs on PostgreSQL; new tests for the migration command, verification, maintenance mode, concurrency. |
| V. Simple, secure by default | Pass (2.0.0) | Raw parameterised `psycopg`, no ORM, CSRF on; `sqlite3` only in `sqlite_import.py`. |
| Tech constraint: Database | Pass (2.0.0) | PostgreSQL only, Docker PostgreSQL for dev and tests. |
| CSP, request limits, uploads, charts, deployment | Pass | No change; maintenance page is a server-rendered template using the existing stylesheet. |

Gate result: pass against constitution 2.0.0, amended on 2026-10-26 before implementation. The
deviations from 1.0.0 that led to the amendment are recorded in Complexity Tracking. Re-check
after design: still pass (see end of [research.md](research.md)).

## Project Structure

### Documentation (this feature)

```text
specs/feature-database-setup/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── migration-cli.md
│   └── configuration.md
└── tasks.md             # created later by /speckit-tasks
```

### Source Code (repository root)

```text
config.py                          # DATABASE_URL, DATABASE_SCHEMA, MAINTENANCE_MODE
compose.yaml                       # NEW: local PostgreSQL for dev and tests
docker/initdb/01-create-test-db.sql  # NEW: creates penny_test next to penny_dev on first start
.env.example                       # DATABASE_URL replaces DATABASE
requirements.txt                   # + psycopg[binary]
expense_tracker/
├── __init__.py                    # register maintenance hook and CLI; init_db unchanged call
├── db.py                          # psycopg connection, schema_version table, baseline migration, advisory lock
├── auth.py                        # %s placeholders, UniqueViolation, lower(username) lookup
├── profile.py                     # %s placeholders, bytea handling
├── routes.py                      # %s placeholders, lower(description) sort, LIMIT/OFFSET
├── sqlite_import.py               # NEW: `migrate` and `verify` commands (only module importing sqlite3)
├── templates/maintenance.html     # NEW: 503 page
└── ...
docs/cutover.md                    # NEW: backup, migrate, verify, switch, rollback runbook
tests/
├── conftest.py                    # PostgreSQL schema-per-test fixture
├── test_db.py                     # rewritten for PostgreSQL migrations
├── test_sqlite_import.py          # NEW: migrate, refuse, atomicity, verify
├── test_maintenance.py            # NEW
└── test_concurrency.py            # NEW
README.md, CLAUDE.md               # updated (FR-015); CLAUDE.md removed from .gitignore
.specify/memory/constitution.md    # amended to 2.0.0 before implementation (FR-015)
```

**Structure Decision**: keep the existing single Flask package. The only new module is
`sqlite_import.py`, which isolates the one remaining use of `sqlite3`.

## Complexity Tracking

| Deviation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| New PostgreSQL migration chain with a baseline instead of replaying SQLite v1-v4 | The SQLite chain contains SQLite-only steps (`PRAGMA`, table rebuilds, float-to-cents prototype conversion) that have no meaning on a new PostgreSQL database | Porting each old step would re-create history nobody needs; a new empty database only needs the current schema. Future changes still append `_migrate_vN`. |
| New dependency `psycopg` | The app needs a PostgreSQL driver | No driver in the standard library; psycopg 3 keeps raw parameterised SQL (no ORM). |
| Constitution amendment | Principle V and the "SQLite only" constraint contradicted the feature | Working around them would leave the project documents wrong. Amended to 2.0.0 before implementation. |
