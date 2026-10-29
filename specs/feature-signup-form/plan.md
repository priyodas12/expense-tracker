# Implementation Plan: Personal Details at Sign-Up

**Branch**: `feature/signup-form` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/feature-signup-form/spec.md`

## Summary

The registration form gains first name, last name, email, mobile, address, gender and
profession. The first four are required. All seven are saved on the existing `profiles` row,
which is now created in the same transaction as the account, and they can be edited on the
profile page under the same rules. Usernames and emails are unique ignoring letter case. Both are
checked on submit, and also when the user leaves the field, through a small JSON endpoint that the
app limits to 20 checks per visitor per minute, counted in PostgreSQL so the limit holds across
every server. Migration v2 splits the old full name into first and last name, adds gender and
profession, and builds a partial unique email index that tolerates emails already shared before
the upgrade. Migration v3 adds the counter table. The Privacy Policy is updated to match.

## Technical Context

**Language/Version**: Python 3.14 (target), Flask 3.1

**Primary Dependencies**: Flask, Flask-WTF, Werkzeug (including `ProxyFix`), psycopg 3; no new
dependency (research R1, R2).

**Storage**: PostgreSQL. `profiles` changed by `_migrate_v2`; new `rate_limit_hits` table in
`_migrate_v3` ([data-model.md](data-model.md)).

**Testing**: pytest and pytest-flask on the Docker PostgreSQL, one schema per test. Concurrency
and shared-limit tests use two app instances on one schema, as `tests/test_concurrency.py` does.

**Target Platform**: Linux server, Gunicorn behind Nginx or Caddy, several servers sharing one
database.

**Project Type**: Web application (server-rendered Flask monolith, plain JavaScript).

**Performance Goals**: early check answers within 1 second for 95% of requests (SC-007);
registration completable in under 2 minutes (SC-001).

**Constraints**: CSP unchanged (scripts from `'self'` only, no inline code or `style`
attributes); 16 KB request bodies; parameterised SQL; no personal details in logs (FR-015);
visitor address must be trustworthy behind the proxy (R2).

**Scale/Scope**: under 100 users today; at most 20 early checks per visitor per minute.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / constraint | Status | Notes |
|---|---|---|
| I. Money is integer cents | Pass | Not affected. |
| II. Single filter pipeline | Pass | Not affected. Profile reads and writes stay keyed on `g.user["id"]`. |
| III. Migrations are append-only | Pass | New `_migrate_v2` and `_migrate_v3`; `_migrate_v1` untouched. The gender list is frozen inside the migration, not imported. README lists both. |
| IV. Test-backed changes | Pass | New tests for registration, profile, early check, limit, migrations and importer ([quickstart.md](quickstart.md)). |
| V. Simple, secure by default | Pass | No new dependency, no ORM, parameterised SQL, CSRF on for the new endpoint, passwords unchanged. |
| Tech constraint: Rate limiting ("not provided by the app; MUST be added at the proxy or via an extension") | **Deviation, justified** | The spec (FR-005e, clarified 2026-10-27) requires the app itself to limit the early check. See Complexity Tracking. |
| Tech constraint: CSP | Pass | One new script file from `'self'`; JSON over `fetch` is allowed by `default-src 'self'`. |
| Tech constraint: Request limits | Pass | Forms stay well under 16 KB; the `before_request` ordering is unchanged. |
| Tech constraint: Uploads, Charts, Deployment | Pass | Not affected; deployment gains one optional setting, `PROXY_TRUSTED_HOPS`. |

Gate result: **pass**, with one justified deviation. Re-check after design: still pass (see the
end of [research.md](research.md)).

## Project Structure

### Documentation (this feature)

```text
specs/feature-signup-form/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1 to R7
├── data-model.md        # Phase 1: profiles changes, rate_limit_hits
├── quickstart.md        # Phase 1: how to validate the feature
├── contracts/
│   ├── registration-form.md   # Registration and profile form fields and messages
│   └── availability-check.md  # POST /auth/check-availability
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks; not created here)
```

### Source Code (repository root)

```text
expense_tracker/
├── __init__.py            # ProxyFix from PROXY_TRUSTED_HOPS
├── auth.py                # register: new fields, one transaction, all errors; check-availability endpoint
├── db.py                  # _migrate_v2 (profiles), _migrate_v3 (rate_limit_hits)
├── profile.py             # profile edit: new fields, own-email rule, clears legacy flag
├── validation.py          # validate_personal_details() shared by register and profile; GENDERS
├── rate_limit.py          # NEW: hit(bucket, limit, window) on rate_limit_hits
├── sqlite_import.py       # split full_name when importing; verify split names
├── static/js/availability.js   # NEW: early check on change, aria-live messages
└── templates/
    ├── register.html      # seven new inputs, message elements, script tag
    ├── profile.html       # first/last name, Mobile, gender, profession, script tag
    └── privacy.html       # section 2 updated (FR-016)
config.py                  # PROXY_TRUSTED_HOPS (default 0)

tests/
├── test_auth.py           # registration fields, errors, uniqueness, race
├── test_profile.py        # new fields, own email, legacy flag cleared
├── test_availability.py   # NEW: endpoint responses, limit across two apps, proxy hops
├── test_db.py             # v2 split, legacy duplicates, index; v3 table
└── test_sqlite_import.py  # importer split

README.md                  # migrations v2 and v3, PROXY_TRUSTED_HOPS, feature notes
```

**Structure Decision**: the existing single Flask package. One new module, `rate_limit.py`,
keeps the counter separate so login rate limiting (README open item) can reuse it later. Shared
field rules live in `validation.py`, next to the current `validate_profile`, so registration and
the profile page can't drift apart.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Rate limiting inside the app, against the constitution's "Rate limiting" constraint | FR-005e (clarified with the user) requires the app itself to limit early checks, working in local and test setups and shared across servers (SC-008). The early check makes probing for accounts easy, so the limit ships with it. | *Proxy rule*: rejected by the user in clarification; it can't be tested in the suite. *Flask-Limiter*: its shared storage needs Redis or similar, a new service plus a dependency (R1). |
| Partial unique email index with a legacy-duplicate flag | The spec requires old accounts that already share an email to keep it, while new and changed emails are unique and race-safe (SC-006). | *Plain unique index*: can't be built while duplicates exist. *App-only check*: two servers can race past it. |

**Follow-up for governance** (not part of this feature's code): amend the constitution's "Rate
limiting" constraint to allow in-app limits backed by the shared database (MINOR bump), and fix
the stale SQLite references in Principle IV and "Uploads" (PATCH). Run `/speckit-constitution`.

**Accepted risk**: two simultaneous registrations using an email held only by flagged legacy
profiles are checked in application code but not by the index (R3). With under 100 users this is
accepted.
