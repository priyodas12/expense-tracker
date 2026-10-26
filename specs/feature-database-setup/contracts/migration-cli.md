# Contract: migration commands

Flask CLI group `sqlite-import`, run from the repository root with the virtualenv active and the
target configured through `DATABASE_URL` (see [configuration.md](configuration.md)).

```bash
flask --app app sqlite-import migrate --source /path/to/expenses.db
flask --app app sqlite-import verify  --source /path/to/expenses.db
```

## `migrate`

| Item | Behaviour |
|---|---|
| Input | `--source PATH` (required): SQLite file. Opened read-only; never written. |
| Start-up | Works with `MAINTENANCE_MODE` on: the command brings the target schema to the current version itself, since app start-up skips that step in maintenance mode. |
| Preconditions | Source `user_version` is 4, else exit 2 with a message to upgrade using the previous release. Target schema is created if missing. Target `users`, `expenses`, `monthly_limits`, `profiles` are all empty, else exit 3 ("target is not empty"). |
| Action | Copies the four tables in one PostgreSQL transaction, preserving ids, cents, hashes, NULL categories and photo bytes, then resets identity sequences. |
| Success | Exit 0. Prints per-table row counts copied. |
| Failure | Exit 1 with a redacted message. The transaction is rolled back, so the target stays empty; the source is untouched; the command can be re-run. |
| Secrets | Output never contains the database URL or password. |

## `verify`

| Item | Behaviour |
|---|---|
| Input | `--source PATH` (required). |
| Checks | Row count per table; per-user sum of `amount_cents`; SHA-256 of each photo; each `password_hash`. |
| Success | Exit 0, prints `OK` with counts. |
| Mismatch | Exit 4, lists each difference (table, key, source value, target value). Photo and hash differences show only digests / user ids, never the values. |
| Side effects | None (read-only on both sides). |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Unexpected error (rolled back) |
| 2 | Source missing, unreadable, or wrong schema version |
| 3 | Target not empty |
| 4 | Verification mismatch |

## Web interface

No routes, forms, query parameters or JSON endpoints change. The only new response is the
maintenance page: HTTP 503 with `Retry-After` for every non-static request while
`MAINTENANCE_MODE` is on.
