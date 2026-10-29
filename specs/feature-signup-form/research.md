# Research: Personal Details at Sign-Up

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-27

Each item resolves an unknown from the plan's Technical Context.

## R1. Where the shared early-check limit is counted

- **Decision**: count early checks in a new PostgreSQL table, `rate_limit_hits`, with one row per
  visitor key and one-minute window. Each check runs a single
  `INSERT ... ON CONFLICT (bucket, window_start) DO UPDATE SET hits = hits + 1 RETURNING hits`,
  and the check is refused when the returned count is above 20. Rows older than five minutes are
  deleted by the same request.
- **Rationale**: every app server already shares the one PostgreSQL database (constitution,
  Database constraint), so a table gives one count across all servers with no new service and no
  new dependency. The upsert is a single atomic statement, so two servers counting the same
  visitor at the same moment can't both slip under the limit. It works unchanged in local
  development and the test suite (FR-005e).
- **Alternatives considered**:
  - *Flask-Limiter*: the usual Flask extension, but its shared storage backends are Redis,
    Memcached, MongoDB and similar. None is PostgreSQL, so it would add both a dependency and a
    new service to run. Its in-memory storage counts per process, which breaks SC-008.
  - *Limit at the reverse proxy* (Nginx `limit_req`): rejected in clarification; the user chose
    an in-app limit.
  - *Advisory locks plus a counter*: more code for the same result as one upsert.

## R2. Identifying a visitor behind the reverse proxy

- **Decision**: wrap the app in Werkzeug's `ProxyFix` with `x_for` set from a new
  `PROXY_TRUSTED_HOPS` setting (default `0`, meaning no proxy). The limit key is the resulting
  `request.remote_addr`.
- **Rationale**: in production Gunicorn sits behind Nginx or Caddy, so without this every visitor
  appears to come from the proxy's address and shares one limit of 20 per minute. Trusting
  `X-Forwarded-For` only for a configured number of hops stops a visitor from forging the header
  to dodge the limit. `ProxyFix` ships with Werkzeug, which is already pinned.
- **Alternatives considered**: always trusting `X-Forwarded-For` (spoofable); keying on the
  session (a script just drops the cookie).

## R3. Email uniqueness when old profiles already share an address

- **Decision**: a partial unique index, `profiles_email_lower`, on `lower(email)` for rows where
  `email <> ''` and `email_legacy_duplicate` is false. Migration v2 sets
  `email_legacy_duplicate = true` on every profile whose email is shared with another profile
  before the index is built, and prints those user ids for the operator. A user's flag is cleared
  the first time they save a profile, which also runs the uniqueness check.
- **Rationale**: the spec requires both old accounts to keep their shared email (Edge Cases) while
  enforcing uniqueness from now on (FR-005, SC-006). A plain unique index can't be built while
  duplicates exist; the partial index lets it be built and makes the database, not just the app,
  enforce uniqueness for every new or changed email, so two simultaneous registrations can't both
  win (SC-006).
- **Alternatives considered**: clearing or rewriting duplicate emails (loses user data, which the
  spec forbids); enforcing uniqueness only in application code (two servers can race past it).
- **Remaining gap**: a new registration is also checked in application code against flagged
  legacy rows, but two requests racing for a flagged legacy address are not stopped by the index.
  With under 100 users and probably no duplicates at all, this is accepted and noted in the plan.

## R4. Splitting the saved full name

- **Decision**: migration v2 adds `first_name` and `last_name`, fills them with
  `split_part(trim(full_name), ' ', 1)` and the rest of the trimmed name after the first space,
  then drops `full_name`.
- **Rationale**: FR-013 and the Edge Cases define the rule (first word, then the remaining words;
  one word leaves the last name empty). Dropping the column leaves one source of truth.
- **Alternatives considered**: keeping `full_name` in sync with the new fields (two sources of
  truth that can drift).
- **Knock-on change**: `sqlite_import.py` copies `profiles.full_name` from the old SQLite file. It
  MUST split the name the same way when inserting, and its verification must compare the split
  values. Its tests change with it.

## R5. Where the new details are stored, and the phone column

- **Decision**: all personal details stay on the existing `profiles` table, one row per user,
  created in the same transaction as the `users` row at registration. The existing `phone` column
  keeps its name; only the label in the forms becomes "Mobile".
- **Rationale**: `profiles` already holds email, phone and address under the same owner-only
  access (FR-014). Renaming the column would touch the importer, tests and templates for no
  user-visible gain.
- **Alternatives considered**: new columns on `users` (splits personal data across two tables);
  renaming `phone` to `mobile` (churn only).

## R6. Shape of the early check endpoint

- **Decision**: `POST /auth/check-availability` with a form body (`field`, `value`, `csrf_token`),
  answering JSON `{"field": ..., "status": "available" | "taken" | "invalid" | "limited"}`. See
  [contracts/availability-check.md](contracts/availability-check.md).
- **Rationale**: POST keeps typed emails out of server and proxy access logs (FR-015), which a
  query string would not. Flask-WTF already protects every POST with CSRF, so the endpoint needs
  no exemption. JSON matches how the chart endpoints answer scripts (constitution, Charts).
  Answering `limited` with HTTP 429 lets the script show nothing, as FR-005e requires.
- **Alternatives considered**: GET with a query string (logs personal data); one endpoint per
  field (duplicated code for the same rules).

## R7. The browser side

- **Decision**: one new script, `static/js/availability.js`, loaded with
  `<script src=... defer>` on the registration and profile pages. It listens for the `change`
  event on the username and email inputs, posts with `fetch`, and writes the result with
  `textContent` into a message element marked `aria-live="polite"`. It never blocks typing or
  submitting, and a failed request shows nothing (FR-005c).
- **Rationale**: plain JavaScript from `'self'` fits the CSP without changes (`default-src 'self'`
  also covers `fetch`). `textContent` avoids XSS. A live region makes the message readable by
  screen readers.
- **Alternatives considered**: checking on every keystroke (wastes the 20-per-minute allowance);
  `innerHTML` (XSS risk).

## Constitution re-check after design

| Principle / constraint | Result |
|---|---|
| I. Money in integer cents | Not affected. |
| II. Single filter pipeline | Not affected; profile access stays keyed on `g.user["id"]`. |
| III. Append-only migrations | Pass: new `_migrate_v2` (profile fields, email index) and `_migrate_v3` (`rate_limit_hits`); v1 untouched; no live constants imported (the gender list is frozen in the migration). |
| IV. Test-backed changes | Pass: tests listed in [quickstart.md](quickstart.md); `tests/test_db.py` covers both migrations. |
| V. Simple, secure by default | Pass: no new dependency; parameterised SQL; CSRF stays on for the new endpoint. |
| Rate limiting constraint | Justified deviation: see plan, Complexity Tracking. |
| CSP | Pass: one external script from `'self'`; no inline script or style. |
| Request limits | Pass: forms stay well under 16 KB. |

Result: pass, with one justified deviation.
