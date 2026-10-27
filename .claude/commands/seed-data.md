---
description: Seed one user with 3 months of expenses across every category (dev only)
argument-hint: "[username] [password] [--reset]  (both generated when omitted)"
allowed-tools: Bash(venv/bin/python:*), Bash(docker compose ps:*), Bash(docker compose up:*)
---

Seed the **development** database with one user and three months of sample
expenses, using the seed script below.

Arguments: `$ARGUMENTS`

## Rules

- Development only. The script refuses to run when `APP_ENV` is
  `production` or unset (the app defaults to production). Never work around that, and never point it at a database
  other than the one in `.env`.
- Use the project's virtualenv Python (`venv/bin/python`), not the system
  `python3`, which doesn't have Flask.
- Do not edit any project files. Run the script exactly as written here.

## Steps

1. Parse the arguments: the first word, if any, is the username, the second
   is the password, and `--reset` anywhere means "delete this user's
   existing expenses first". A username given must match
   `^[A-Za-z0-9_.-]{3,30}$` and a password given must be 8 to 128
   characters (the same rules as registration). If not, say why and stop.
   Never invent credentials yourself and never fall back to a fixed one:
   when the username or password is omitted, leave its variable empty and
   the script generates it.
   - Generated username: a realistic `first.last` handle with a two-digit
     suffix (e.g. `maya.okafor47`), re-rolled until it isn't taken.
   - Generated password: 20 characters from `secrets`, with at least one
     upper-case letter, lower-case letter, digit and symbol.
2. Check PostgreSQL is running with `docker compose ps`. If it isn't, start
   it with `docker compose up -d`.
3. Run the script from the project root, passing the parsed values as
   environment variables (`SEED_USERNAME`, `SEED_PASSWORD`, and
   `SEED_RESET=1` only when `--reset` was given). Leave `SEED_USERNAME` or
   `SEED_PASSWORD` empty (`''`) when it wasn't given:

   ```bash
   SEED_USERNAME='<username>' SEED_PASSWORD='<password>' SEED_RESET=<0|1> venv/bin/python - <<'PY'
   import os
   import random
   import secrets
   import string
   import sys
   from datetime import date, timedelta

   from werkzeug.security import generate_password_hash

   from expense_tracker import create_app
   from expense_tracker.db import get_db
   from expense_tracker.validation import CATEGORIES

   MONTHS = 3
   MIN_PER_MONTH = 20

   # (description choices, min cents, max cents) per category.
   CATALOGUE = {
       "Food": (["Groceries", "Lunch", "Coffee", "Dinner out", "Bakery", "Takeaway"], 300, 6500),
       "Rent": (["Monthly rent"], 90000, 90000),
       "Shopping": (["Clothes", "Shoes", "Home goods", "Electronics accessory"], 1500, 12000),
       "Bills": (["Electricity", "Internet", "Mobile plan", "Water", "Gas"], 2000, 9000),
       "Study": (["Online course", "Books", "Stationery", "Exam fee"], 800, 15000),
       "Travel": (["Train ticket", "Hotel night", "Flight", "Weekend trip"], 3000, 25000),
       "Transport": (["Bus pass", "Taxi", "Fuel", "Parking", "Metro top-up"], 250, 6000),
       "Health": (["Pharmacy", "Doctor visit", "Gym membership", "Dentist"], 800, 12000),
       "Entertainment": (["Cinema", "Concert", "Streaming", "Board game night"], 600, 8000),
       "Gifts": (["Birthday gift", "Flowers", "Wedding gift"], 1500, 10000),
       "Personal": (["Haircut", "Toiletries", "Laundry"], 500, 4500),
       "Other": (["Charity donation", "Post office", "Misc"], 200, 5000),
   }
   # Categories that get the extra entries beyond one per category.
   FREQUENT = ["Food", "Food", "Food", "Transport", "Transport", "Entertainment",
               "Shopping", "Personal", "Bills", "Health"]

   FIRST_NAMES = ["maya", "liam", "aisha", "noah", "priya", "lucas", "sofia", "omar",
                  "elena", "kenji", "zara", "mateo", "ines", "arjun", "chloe", "tomas"]
   LAST_NAMES = ["okafor", "bennett", "sharma", "nakamura", "rossi", "haddad", "fischer",
                 "silva", "kowalski", "mensah", "dubois", "lindqvist", "reyes", "park"]
   PASSWORD_LENGTH = 20
   PASSWORD_SYMBOLS = "!@#$%^&*-_=+?"

   username = os.environ.get("SEED_USERNAME", "").strip()
   password = os.environ.get("SEED_PASSWORD", "")
   reset = os.environ.get("SEED_RESET") == "1"
   password_generated = not password

   if os.environ.get("APP_ENV", "production") == "production":
       sys.exit("Refusing to seed: APP_ENV is production or unset. Set APP_ENV=development in .env.")
   missing = set(CATEGORIES) - set(CATALOGUE)
   if missing:
       sys.exit(f"Seed catalogue is missing categories: {', '.join(sorted(missing))}")


   def generate_username(db):
       """A realistic first.last handle with a two-digit suffix that no user has yet."""
       while True:
           name = (f"{secrets.choice(FIRST_NAMES)}.{secrets.choice(LAST_NAMES)}"
                   f"{secrets.randbelow(90) + 10}")
           taken = db.execute(
               "SELECT 1 FROM users WHERE lower(username) = lower(%s)", (name,)
           ).fetchone()
           if taken is None:
               return name


   def generate_password():
       """A random password with at least one of each character class."""
       classes = [string.ascii_uppercase, string.ascii_lowercase, string.digits, PASSWORD_SYMBOLS]
       alphabet = "".join(classes)
       chars = [secrets.choice(c) for c in classes]
       chars += [secrets.choice(alphabet) for _ in range(PASSWORD_LENGTH - len(chars))]
       secrets.SystemRandom().shuffle(chars)
       return "".join(chars)


   def month_starts(today, count):
       """First day of the current month and the count - 1 months before it, oldest first."""
       starts = [today.replace(day=1)]
       for _ in range(count - 1):
           starts.append((starts[-1] - timedelta(days=1)).replace(day=1))
       return list(reversed(starts))


   def last_day(start, today):
       next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
       return min(next_month - timedelta(days=1), today)


   def month_rows(rng, start, today):
       end = last_day(start, today)
       span = (end - start).days
       categories = list(CATEGORIES) + FREQUENT
       while len(categories) < MIN_PER_MONTH:
           categories.append(rng.choice(FREQUENT))
       rows = []
       for category in categories:
           descriptions, low, high = CATALOGUE[category]
           if category == "Rent":
               day = start
           else:
               day = start + timedelta(days=rng.randint(0, span))
           # Round to whole 5 cents so the amounts look like real prices.
           cents = rng.randint(low // 5, high // 5) * 5
           rows.append((rng.choice(descriptions), cents, category, day.isoformat()))
       return rows


   app = create_app()
   with app.app_context():
       db = get_db()
       if not username:
           username = generate_username(db)
       if password_generated:
           password = generate_password()
       user = db.execute(
           "SELECT id FROM users WHERE lower(username) = lower(%s)", (username,)
       ).fetchone()
       if user is None:
           user = db.execute(
               "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
               (username, generate_password_hash(password)),
           ).fetchone()
           print(f"Created user {username!r}.")
           print(f"Username: {username}")
           print(f"Password: {password}" + (" (generated)" if password_generated else ""))
       else:
           existing = db.execute(
               "SELECT count(*) AS n FROM expenses WHERE user_id = %s", (user["id"],)
           ).fetchone()["n"]
           if existing and not reset:
               sys.exit(
                   f"User {username!r} already has {existing} expenses. "
                   "Run again with --reset to replace them."
               )
           db.execute("DELETE FROM expenses WHERE user_id = %s", (user["id"],))
           print(f"Using existing user {username!r} (password unchanged); removed {existing} expenses.")

       today = date.today()
       rng = random.Random(f"{username}-{today.isoformat()}")
       summary = []
       for start in month_starts(today, MONTHS):
           rows = month_rows(rng, start, today)
           db.cursor().executemany(
               "INSERT INTO expenses (user_id, description, amount_cents, category, date) "
               "VALUES (%s, %s, %s, %s, %s)",
               [(user["id"], *row) for row in rows],
           )
           summary.append((start.strftime("%Y-%m"), len(rows), sum(r[1] for r in rows)))
       db.commit()

       for month, count, cents in summary:
           print(f"{month}: {count} expenses, total {cents // 100}.{cents % 100:02d}")
       print(f"All {len(CATEGORIES)} categories present in every month.")
   PY
   ```

4. Report the result in a few lines: the username, whether it was created
   or reused, and the per-month counts and totals the script printed. If the
   user was created, give the username and password exactly as the script
   printed them, in a code block so they can be copied, and say they can log
   in at http://127.0.0.1:5000. Say that a generated password is shown only
   this once (only its hash is stored), so they should save it now. If the
   user was reused, say the existing password is unchanged. If the script
   stopped because the user already has expenses, say so and suggest
   `/seed-data <username> --reset`.
