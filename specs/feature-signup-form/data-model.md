# Data Model: Personal Details at Sign-Up

**Feature**: [spec.md](spec.md) | **Research**: [research.md](research.md) | **Date**: 2026-10-27

Two new migrations are appended to `MIGRATIONS` in `db.py`. Each runs in its own transaction.

## `users` (unchanged)

| Column | Type | Notes |
|---|---|---|
| `id` | bigint identity | Primary key |
| `username` | text | Unique ignoring case (`users_username_lower`, existing) |
| `password_hash` | text | Werkzeug hash |

## `profiles` (changed by `_migrate_v2`)

One row per user. Registration now always creates it, in the same transaction as the `users` row
(FR-010). Accounts created before this change may have no row; one is created on their first save.

| Column | Type | Change | Rules (from the spec) |
|---|---|---|---|
| `user_id` | bigint | unchanged | Primary key, references `users(id)` on delete cascade |
| `first_name` | text not null default `''` | **new** | Required at registration and on save; trimmed; at most 100 characters; letters from any language, spaces, hyphens, apostrophes (FR-002, FR-003) |
| `last_name` | text not null default `''` | **new** | Same rules as first name |
| `full_name` | text | **dropped** | Split into first and last name first (R4) |
| `email` | text not null default `''` | unchanged column, new index | Required; valid format; at most 254 characters; unique ignoring case (FR-004, FR-005) |
| `email_legacy_duplicate` | boolean not null default false | **new** | True only for profiles that shared an email before v2 (R3); cleared on the user's next save |
| `phone` | text not null default `''` | unchanged (labelled "Mobile") | Required; at least 7 digits; at most 20 characters; digits, spaces, `+`, `-`, brackets (FR-006) |
| `address` | text not null default `''` | unchanged | Optional; at most 300 characters; may span lines (FR-007) |
| `gender` | text not null default `''` | **new** | Optional; `CHECK (gender IN ('', 'Female', 'Male'))` (FR-008) |
| `profession` | text not null default `''` | **new** | Optional; at most 100 characters (FR-009) |
| `photo`, `photo_type` | bytea, text | unchanged | |

**Index**: `profiles_email_lower`, unique on `lower(email)` where `email <> ''` and
`NOT email_legacy_duplicate`.

**Migration v2 steps** (one transaction):

1. Add `first_name`, `last_name`, `gender`, `profession`, `email_legacy_duplicate`.
2. Fill `first_name` and `last_name` from `trim(full_name)`: first word, then the rest (R4).
3. Drop `full_name`.
4. Set `email_legacy_duplicate = true` where `lower(email)` (non-empty) appears on more than one
   profile, and log the affected user ids (ids only, never the email; FR-015).
5. Add the gender check constraint and create `profiles_email_lower`.

## `rate_limit_hits` (new, `_migrate_v3`)

Counts early username and email checks per visitor per minute, shared by every app server (R1).

| Column | Type | Notes |
|---|---|---|
| `bucket` | text not null | `availability:<visitor network address>` |
| `window_start` | timestamptz not null | Start of the one-minute window (`date_trunc('minute', now())`) |
| `hits` | integer not null | Checks made in this window |

**Primary key**: (`bucket`, `window_start`). **Index**: on `window_start`, for cleanup.

Rows older than five minutes are deleted by each check. The table holds network addresses only,
for at most five minutes, and no personal details.

## Validation and lifecycle

- **Registration** (FR-001 to FR-011, FR-005a): all fields are validated together and every error
  is returned. Username and email are each checked for existing use (email against all profiles,
  including legacy duplicates). Then `users` and `profiles` rows are inserted in one transaction.
  A unique-index violation from a simultaneous registration is turned into the same "already
  taken" or "already in use" message, never an error page.
- **Profile save** (FR-012, FR-005): the same field rules, and the four required fields, apply.
  The email may equal the user's own current email; any other account's email is rejected. A
  successful save clears `email_legacy_duplicate`.
- **Early check** (FR-005b to FR-005e): read-only lookups plus one counter update; never changes
  `users` or `profiles`.

## Importer change (`sqlite_import.py`)

The old SQLite file still has `profiles.full_name`. `_copy_profiles` splits it into `first_name`
and `last_name` with the same rule as migration v2, and leaves `gender` and `profession` empty.
The verification step compares the split names instead of `full_name`.
