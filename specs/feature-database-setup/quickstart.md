# Quickstart: validating the PostgreSQL migration

Run these after implementation to prove the feature end to end. Details of each interface are in
[contracts/](contracts/) and [data-model.md](data-model.md).

## Prerequisites

- Docker with the Compose plugin
- Python virtualenv with `pip install -r requirements.txt`
- A copy of a populated SQLite database at schema version 4 (not the live file)

## 1. Start local PostgreSQL

```bash
docker compose up -d
docker compose ps        # postgres is "healthy"
```

Expected: the service is healthy; `penny_dev` and `penny_test` exist.

## 2. Run the test suite on PostgreSQL

```bash
pytest
```

Expected: all tests pass (SC-003), including migration, maintenance and concurrency tests.

## 3. Start the app on a fresh database

```bash
export DATABASE_URL=postgresql://penny:penny@localhost:5432/penny_dev
python app.py
```

Expected: the app starts and creates the schema without manual steps. Register, log in, add, edit,
filter, sort, export and delete expenses; set a monthly limit; upload a photo (User Story 2).

## 4. Migrate a copy of real data

```bash
cp /path/to/expenses.db /tmp/expenses-copy.db       # or the scratch directory
flask --app app sqlite-import migrate --source /tmp/expenses-copy.db
flask --app app sqlite-import verify  --source /tmp/expenses-copy.db
```

Expected: `migrate` exits 0 and prints counts; `verify` exits 0 and prints `OK`. Existing users can
log in with their old passwords (SC-001, SC-002).

Negative checks:
- Run `migrate` again: exits 3 (target not empty).
- Point `--source` at a non-version-4 file: exits 2 and the target stays empty.

## 5. Maintenance mode

```bash
MAINTENANCE_MODE=1 python app.py
```

Expected: every page returns 503 with the maintenance page and no database connection is made
(FR-018).

## 6. Two servers, one database

Start two instances on different ports with the same `DATABASE_URL` and `SECRET_KEY`, then run the
concurrency test or post expenses to both at once.

Expected: all writes saved, logins valid on both (User Story 3, SC-004).

## 7. Cutover rehearsal

Follow `docs/cutover.md` on the copy: backup, maintenance on, migrate, verify, smoke check on a
private `127.0.0.1` instance, rollback within the window, then repeat and close the window
(User Story 4, SC-006).
