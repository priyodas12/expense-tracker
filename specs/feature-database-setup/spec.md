# Feature Specification: Database Migration to PostgreSQL

**Feature Branch**: `feature/database-setup`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "db-migration-to-postgres"

## Clarifications

### Session 2026-10-26

- Q: After the move to PostgreSQL, should the app still be able to run on SQLite for local development and tests? → A: No. PostgreSQL everywhere, with a Docker-hosted local PostgreSQL for development and tests. SQLite remains only as the source of the one-time data migration.
- Q: Should the cutover keep the app offline for the whole data move, or can users keep reading while it runs? → A: Fully offline. The app shows a maintenance page during the data move.
- Q: If something goes wrong after the app is back online on PostgreSQL, should rolling back to the old SQLite database also carry over expenses saved after the cutover? → A: No. Rollback is only supported during a verification window before the app reopens to users, so no post-cutover data exists to lose.
- Q: Roughly how much data does the live app hold (users and expenses)? → A: Under 100 users and under 100,000 expenses in total.
- Q: Which git branch carries this feature? → A: `feature/database-setup` (the existing branch). No separate `001-...` branch is created.
- Q: What should the spec folder be named? → A: After the feature branch, `specs/feature-database-setup` (the slash in the branch name is replaced with a hyphen so it stays one folder), not `001-db-migration-to-postgres`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Move existing data to the new database without loss (Priority: P1)

The operator has a live Expense Tracker whose data sits in a single-file database. They want to move
all of it to a PostgreSQL database so the app can later run on more than one server. They run a
one-time migration, and afterwards every user can log in and sees exactly the same expenses, monthly
limits, and profile details (including photos) as before.

**Why this priority**: Without a safe, lossless data move there is no feature. Losing or altering
user financial data is the worst possible outcome.

**Independent Test**: Take a copy of a populated database, run the migration into an empty
PostgreSQL database, and compare record counts, per-user totals, limits, and profile data between
source and target. The result delivers value on its own: a verified copy of the data.

**Acceptance Scenarios**:

1. **Given** a source database with users, expenses, monthly limits and profiles with photos, **When** the operator runs the migration into an empty PostgreSQL database, **Then** every record is present in the target and per-user expense totals match the source to the cent.
2. **Given** a migration that fails part-way, **When** the operator inspects the target, **Then** no partial data is left behind and the source database is untouched, so the migration can be re-run.
3. **Given** a completed migration, **When** the operator runs the built-in verification, **Then** it reports matching counts and totals for every table and flags any mismatch.

---

### User Story 2 - Run the app against PostgreSQL (Priority: P1)

After the data is moved, the operator points the app at the PostgreSQL database. Every existing
feature (register, login, expense add/edit/delete, filters, sorting, pagination, charts, budget
limit, CSV/PDF export, profile and photo upload) behaves exactly as it did before.

**Why this priority**: The move is only useful if the app works on the new database.

**Independent Test**: Start the app against a freshly migrated PostgreSQL database and run the full
automated test suite plus a manual walkthrough of each page.

**Acceptance Scenarios**:

1. **Given** the app configured for PostgreSQL, **When** a user logs in and browses, filters, sorts and exports their expenses, **Then** results, totals and chart figures are identical to those from the same data on the old database.
2. **Given** two users with their own data, **When** one requests the other's expense, **Then** the app still returns "not found".
3. **Given** a new empty PostgreSQL database, **When** the app starts, **Then** the schema is created up to the current version without manual steps.

---

### User Story 3 - Concurrent use from multiple servers (Priority: P2)

The operator runs more than one app server against the same PostgreSQL database. Users on different
servers add and edit expenses at the same time with no lost updates and no "database is locked"
errors.

**Why this priority**: This is the reason for the move, but it depends on Stories 1 and 2.

**Independent Test**: Run two app instances against one database and perform simultaneous writes
from different users; confirm every write is saved and visible from both instances.

**Acceptance Scenarios**:

1. **Given** two servers sharing one database, **When** users on each save expenses at the same moment, **Then** all expenses are saved and appear in the correct user's list on either server.
2. **Given** a user session started on one server, **When** the next request is served by the other server, **Then** the user is still logged in.

---

### User Story 4 - Documented, repeatable cutover and rollback (Priority: P3)

The operator follows a written procedure for backing up, migrating, switching over, and rolling back
to the old database if something goes wrong.

**Why this priority**: Reduces operational risk but does not change app behaviour.

**Independent Test**: A person unfamiliar with the work follows the procedure on a test copy and
completes cutover and rollback without outside help.

**Acceptance Scenarios**:

1. **Given** the written procedure, **When** the operator follows it on a test copy, **Then** they complete backup, migration, verification and switch-over successfully.
2. **Given** a problem found during the verification window (after switch-over but before the app reopens to users), **When** the operator follows the rollback steps, **Then** the app runs again on the original database with no data from before the cutover lost.
3. **Given** the app has reopened to users, **When** the operator reads the procedure, **Then** it states that rollback is no longer supported and that problems are fixed forward on PostgreSQL.

---

### Edge Cases

- Source database is at an older schema version: migration must upgrade it first or refuse with a clear message.
- Source contains legacy expenses with no category: they must be carried over unchanged.
- Profile photos at the maximum allowed size must transfer byte-for-byte.
- Expenses with zero, very large, or boundary amounts must keep exact cent values.
- Target database is not empty: the migration must refuse instead of overwriting or merging.
- Target database is unreachable or credentials are wrong: the app and migration must fail with a clear, non-secret error message.
- A user visiting during the data move must see a clear maintenance page, and no writes may reach the source database once the move has started.
- Identifier numbering in the target must continue after the highest migrated record so new records do not collide with migrated ones.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support PostgreSQL as the database for all stored data (users, expenses, monthly limits, profiles, photos).
- **FR-002**: The system MUST provide a one-time migration that copies all existing data from the current single-file database to an empty PostgreSQL database.
- **FR-003**: The migration MUST preserve every money amount exactly as whole cents, with no rounding or conversion errors.
- **FR-004**: The migration MUST preserve users' password hashes so existing users can log in without resetting passwords.
- **FR-005**: The migration MUST be all-or-nothing: on any failure the target is left empty and the source is unmodified.
- **FR-006**: The migration MUST refuse to run against a non-empty target.
- **FR-007**: The system MUST provide a verification step that compares record counts and per-user expense totals between source and target and reports any difference.
- **FR-008**: A new, empty PostgreSQL database MUST be brought to the current schema version automatically, through a new versioned migration chain that starts from a baseline equal to the current schema and is append-only from then on.
- **FR-009**: All existing user-facing behaviour (authentication, expense management, filters, sorting, pagination, charts, budget limit, CSV and PDF export, profile and photo upload, security headers, CSRF) MUST work unchanged on PostgreSQL.
- **FR-010**: Per-user data isolation MUST be preserved: a user MUST NOT be able to read or change another user's data.
- **FR-011**: Multiple app servers MUST be able to write to the same database concurrently without lost updates.
- **FR-012**: The database location and credentials MUST be supplied through configuration. Real (non-development) credentials MUST NOT be committed to the repository and MUST NOT appear in logs or error pages. The fixed development-only credentials of the local Docker database may be committed in `compose.yaml` and `.env.example`, clearly labelled as such.
- **FR-013**: The automated test suite MUST run against PostgreSQL and pass in full.
- **FR-014**: The project MUST include a written cutover and rollback procedure, including a backup step before migration.
- **FR-015**: Existing project documentation (README, CLAUDE.md) and the project constitution MUST be updated to reflect the new database support, since the constitution currently states SQLite only.
- **FR-016**: PostgreSQL MUST be the only database the running app supports, in every environment. Local development and automated tests MUST use a PostgreSQL database hosted in a local Docker container. SQLite MUST remain readable only as the source of the one-time data migration (FR-002).
- **FR-017**: The project MUST provide a single documented command or file to start the local Docker PostgreSQL used for development and tests, so a new developer can run the app and the test suite without installing PostgreSQL directly.
- **FR-018**: During the data move the app MUST be offline and MUST show users a maintenance page; no new data may be accepted until the operator brings the app back up on PostgreSQL.
- **FR-019**: The procedure MUST define a verification window after switch-over during which the app stays closed to users while the operator runs the verification step (FR-007) and a smoke check. Rollback to the original SQLite database MUST be supported only within this window, and the original database MUST be kept unmodified until the window closes. No reverse migration from PostgreSQL to SQLite is required.

### Key Entities *(include if feature involves data)*

- **User**: An account with login name and password hash; owns expenses, a monthly limit and a profile.
- **Expense**: A dated spending record owned by one user, with an amount in whole cents, a category (possibly empty for legacy records) and a description.
- **Monthly Limit**: At most one optional spending limit per user, in whole cents.
- **Profile**: Personal details and an optional photo, at most one per user.
- **Schema Version**: The recorded version of the database structure, used to decide which upgrades still need to run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After migration, 100% of users, expenses, limits and profiles from the source are present in the target, with zero differences in record counts and per-user totals.
- **SC-002**: Every existing user can log in with their current password after cutover (0 forced password resets).
- **SC-003**: 100% of the automated test suite passes against PostgreSQL.
- **SC-004**: With two app servers sharing one database, 100 simultaneous expense saves from different users all succeed with 0 lost or duplicated records.
- **SC-005**: Pages that list or chart a user's expenses load in under 2 seconds for a user with 10,000 expenses.
- **SC-006**: An operator following the written procedure completes migration, verification and cutover on a test copy of a 100 MB database in under 30 minutes of active work, and can roll back in under 15 minutes.
- **SC-007**: No database credentials appear in the repository, application logs, or any page shown to users.

## Assumptions

- The operator is a single person or small team responsible for deployment; end users do not take part in the migration.
- The app is fully offline during the data move, showing a maintenance page. Read-only mode and live dual-writing are out of scope.
- Expected scale is under 100 users and under 100,000 expenses in total; larger volumes are out of scope for this feature.
- The migration is a one-time move per deployment, not continuous synchronisation.
- PostgreSQL is provided and managed by the operator; installing and securing the database server is out of scope.
- Moving to a different relational engine other than PostgreSQL is out of scope.
- Features listed as known limitations (rate limiting, account deletion, per-month limits, live limit card, legacy uncategorised expenses, policy pages) are out of scope.
- Developers have Docker available on their machines; developers without it are out of scope.
- Existing behaviour, screens and URLs do not change; no new user-facing features are added.
- The constitution was amended to 2.0.0 before implementation (PostgreSQL only, raw `psycopg`, baseline migration chain), so this feature complies with it.
