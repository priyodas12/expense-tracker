# Quickstart: Personal Details at Sign-Up

How to check the feature works, end to end. Field rules are in
[contracts/registration-form.md](contracts/registration-form.md); the early check is in
[contracts/availability-check.md](contracts/availability-check.md); tables are in
[data-model.md](data-model.md).

## Prerequisites

```bash
source venv/bin/activate
docker compose up -d          # PostgreSQL for dev and tests
```

`.env` has `APP_ENV=development` and a `SECRET_KEY`.

## 1. Automated tests

```bash
pytest                                   # full suite must pass (constitution IV)
pytest tests/test_auth.py                # registration fields, errors, uniqueness
pytest tests/test_profile.py             # profile edit rules, own email allowed
pytest tests/test_availability.py        # early check responses and the limit
pytest tests/test_db.py                  # migrations v2 and v3
pytest tests/test_sqlite_import.py       # importer splits full_name
```

The tests MUST cover at least:

| Area | Expected |
|---|---|
| Register with all seven details | Account and profile created; profile page shows each value |
| Register with only the four required details | Account created; address, gender, profession empty |
| Missing first name and invalid email together | No account; both errors shown; values kept except password |
| Username `ANA` and email `Ana@Example.com` when `ana`/`ana@example.com` exist | No account; both "taken" messages |
| Gender `Other` submitted | Rejected |
| Two registrations with the same email at once (two app instances) | Exactly one account |
| Early check: taken, available, invalid | `taken`, `available`, `invalid`, never account details |
| 21 early checks in a minute across two app instances | 21st answers 429 `limited` |
| `PROXY_TRUSTED_HOPS=1` with `X-Forwarded-For` | Limit keyed on the forwarded address |
| Migration v2 on a profile with `full_name` "Ana Maria Silva" | First "Ana", last "Maria Silva" |
| Migration v2 with two profiles sharing an email | Both kept and flagged; index built |
| Logs during registration and early checks | No email, mobile, name or address |

## 2. Manual check in the browser

```bash
python app.py                            # http://127.0.0.1:5000
```

1. Open **Register**. Fill in every field and submit. Log in; open **Profile**; every value is
   there, and Phone now reads **Mobile**.
2. Log out and register again with the same username in capitals. Leave the field: "Username is
   already taken." appears before submitting.
3. Type the first account's email in different capitals and leave the field: "Email is already in
   use." appears. Submit anyway: the account is not created and both messages show.
4. Turn off JavaScript in the browser and repeat step 3: the same messages appear after
   submitting.
5. Open the browser console: no CSP errors on the registration or profile page.
6. Open **Privacy Policy**: section 2 lists the new details.

## 3. Upgrade check on existing data

1. Before switching to this branch, seed a user (`/seed-data`) and save a full name such as
   "Ana Maria Silva" on their profile.
2. Switch branches and start the app; migrations v2 and v3 run once.
3. Log in as that user: the expense list opens as before, and the profile shows first name "Ana",
   last name "Maria Silva", with the old email, phone and address kept.
