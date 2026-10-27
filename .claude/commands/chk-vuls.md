---
description: Scan for secrets about to be committed, vulnerable dependencies and insecure code
argument-hint: "[--staged-only]"
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git ls-files:*), Bash(git check-ignore:*), Bash(git log:*), Bash(venv/bin/python:*), Read, Grep, Glob
---

Run a security check of this project and report what you find. This is a
**read-only** check: do not edit, stage, unstage, commit or delete anything,
and do not install packages. If you find a problem, report it and suggest the
fix; only make changes if the user asks afterwards.

Arguments: `$ARGUMENTS` (`--staged-only` means run only part 1).

Never print a full secret in your report. Use the masked values the scripts
print (first 4 characters, then `…`).

## Context

Staged files:
!`git diff --cached --name-status`

Untracked files that are *not* ignored (a `git add .` would stage these):
!`git ls-files --others --exclude-standard`

## Part 1: sensitive data marked for commit

Run this from the project root. It scans the staged content (what would
actually be committed, not the working copy), untracked files that are not
ignored, all tracked files, and the git history, and prints findings with
masked values.

```bash
venv/bin/python - <<'PY'
import re
import subprocess
from pathlib import PurePosixPath

PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})\b"),
    "Anthropic API key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    "OpenAI API key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "Stripe key": re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}"),
    "database URL with password": re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^:\s/@]+:([^@\s]+)@"),
    "SECRET_KEY value": re.compile(r"\bSECRET_KEY\s*[=:]\s*['\"]?([^\s'\"#]{8,})"),
    "hard-coded secret": re.compile(
        r"(?i)\b(?:password|passwd|secret|api_?key|access_?token|auth_?token)\b\s*[=:]\s*['\"]([^'\"\s]{8,})['\"]"
    ),
}
# Development-only values that are documented in the repo and expected.
ALLOWED = {"penny:penny@"}
# Values that are references or placeholders, not secrets.
PLACEHOLDER = re.compile(r"(?i)^(<|os\.|getenv|environ|\$\{?|\{\{|your|change|example|replace|xxx|\*\*\*)")
SENSITIVE_NAMES = re.compile(
    r"(?i)(^|/)(\.env(\..+)?|.*\.(pem|key|p12|pfx|jks|keystore|db|sqlite3?|sql|dump|bak)|id_(rsa|ed25519|ecdsa)"
    r"|credentials(\.json)?|.*secret.*\.(json|ya?ml|txt))$"
)
SAFE_NAMES = {".env.example"}
TEXT_LIMIT = 1_000_000  # skip very large blobs


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, errors="replace").stdout


def mask(value):
    return value[:4] + "…" if len(value) > 4 else "…"


def scan_text(text):
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if any(a in line for a in ALLOWED):
            continue
        for label, pattern in PATTERNS.items():
            for m in pattern.finditer(line):
                value = m.group(1) if m.groups() else m.group(0)
                if PLACEHOLDER.match(value):
                    continue
                hits.append((lineno, label, mask(value)))
    return hits


def report(scope, path, hits):
    for lineno, label, masked in hits:
        print(f"  [{scope}] {path}:{lineno}: {label} ({masked})")


def flag_name(scope, path):
    name = PurePosixPath(path).name
    if name not in SAFE_NAMES and SENSITIVE_NAMES.search(path):
        print(f"  [{scope}] {path}: sensitive file type")
        return True
    return False


found = False

print("== Staged (will be committed) ==")
for path in git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines():
    found |= flag_name("staged", path)
    blob = git("show", f":{path}")
    if len(blob) <= TEXT_LIMIT:
        hits = scan_text(blob)
        report("staged", path, hits)
        found |= bool(hits)

print("== Untracked, not ignored (a `git add .` would stage these) ==")
for path in git("ls-files", "--others", "--exclude-standard").splitlines():
    found |= flag_name("untracked", path)
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read(TEXT_LIMIT + 1)
    except OSError:
        continue
    if len(text) <= TEXT_LIMIT:
        hits = scan_text(text)
        report("untracked", path, hits)
        found |= bool(hits)

print("== Already tracked ==")
for path in git("ls-files").splitlines():
    found |= flag_name("tracked", path)
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read(TEXT_LIMIT + 1)
    except OSError:
        continue
    if len(text) <= TEXT_LIMIT:
        hits = scan_text(text)
        report("tracked", path, hits)
        found |= bool(hits)

print("== Git history (added lines in past commits) ==")
commit = path = None
for line in git("log", "-p", "--all", "--no-color", "--format=commit %h").splitlines():
    if line.startswith("commit "):
        commit = line.split()[1]
    elif line.startswith("+++ b/"):
        path = line[6:]
    elif line.startswith("+") and not line.startswith("+++"):
        for _, label, masked in scan_text(line[1:]):
            print(f"  [history {commit}] {path}: {label} ({masked})")
            found = True

print("== .gitignore coverage ==")
for path in [".env", ".env.production", "expenses.db", "server.pem", "server.key", "id_rsa", "dump.sql"]:
    if subprocess.run(["git", "check-ignore", "-q", path]).returncode:
        print(f"  {path}: NOT ignored")
        found = True

print("\nRESULT:", "findings above" if found else "no sensitive data found")
PY
```

Then review the result yourself:
- For each hit, open the line and decide whether it is a real secret or a
  false positive (a test fixture, a placeholder, a variable name). Say which.
- Treat anything in **staged** as the most urgent: it is about to be
  committed. Suggest `git restore --staged <file>` and moving the value to
  `.env`.
- For a secret in **history**, say that removing it from the latest commit
  is not enough: the secret must be rotated, and the history rewritten if the
  repo has been pushed.
- Look at the staged and untracked file lists above for anything that
  shouldn't be in the repo even without a pattern match (database files,
  dumps, editor folders, large binaries, personal notes).

If `$ARGUMENTS` contains `--staged-only`, stop here and report.

## Part 2: vulnerable dependencies

Check the pinned packages in `requirements.txt` against the OSV database
(osv.dev, Google's open vulnerability database for PyPI). Only package names
and versions are sent.

```bash
venv/bin/python - <<'PY'
import json
import re
import urllib.request

pins = []
with open("requirements.txt") as f:
    for line in f:
        m = re.match(r"^\s*([A-Za-z0-9_.\-\[\]]+?)(?:\[.*\])?\s*==\s*([^\s;#]+)", line)
        if m:
            pins.append((m.group(1), m.group(2)))
unpinned = [l.strip() for l in open("requirements.txt") if l.strip() and not l.startswith("#") and "==" not in l]


def post(url, payload):
    req = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


queries = [{"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in pins]
results = post("https://api.osv.dev/v1/querybatch", {"queries": queries})["results"]

vulnerable = 0
for (name, version), result in zip(pins, results):
    ids = [v["id"] for v in result.get("vulns", [])]
    if not ids:
        continue
    vulnerable += 1
    print(f"{name}=={version}")
    for vid in ids:
        vuln = get(f"https://api.osv.dev/v1/vulns/{vid}")
        fixed = sorted({
            e["fixed"]
            for a in vuln.get("affected", []) if a["package"]["name"].lower() == name.lower()
            for r in a.get("ranges", []) for e in r.get("events", []) if "fixed" in e
        })
        severity = vuln.get("database_specific", {}).get("severity", "")
        aliases = ", ".join(a for a in vuln.get("aliases", []) if a.startswith("CVE-"))
        print(f"  {vid} {aliases} {severity}".rstrip())
        print(f"    {vuln.get('summary', '(no summary)')}")
        print(f"    fixed in: {', '.join(fixed) or 'no fix released'}")

print(f"\nChecked {len(pins)} pinned packages; {vulnerable} with known vulnerabilities.")
if unpinned:
    print("Not pinned (not checked): " + ", ".join(unpinned))
PY
```

If the request fails (no network), say the dependency check was skipped and
suggest `pip install pip-audit && pip-audit -r requirements.txt` as an
alternative. For each vulnerable package, recommend the lowest fixed version
and note that dependency versions are changed deliberately in this project,
so the upgrade needs its own commit and a full `pytest` run.

## Part 3: insecure code

Review the application code (`expense_tracker/`, `app.py`, `config.py`,
templates and `static/js/`) with Grep and Read. Skip `venv/`, `tests/` and
`__pycache__/` except where a check says otherwise. Check each item and
report only real problems, with `file:line`:

1. **SQL injection.** Every `execute`/`executemany` must use `%s` or
   `%(name)s` placeholders. Flag any f-string, `%` formatting, `.format()` or
   `+` concatenation that puts request data into SQL. (The f-strings in
   `db.py` migrations built from the frozen `_PG_V1_CATEGORIES` constant and
   the validated schema name are known and safe; confirm they still are.)
2. **Access control.** Every route that reads or changes user data has
   `@login_required`, and single-expense routes load rows through
   `get_owned_expense()` (or filter by `user_id = g.user["id"]`), never by id
   alone.
3. **XSS.** Flag `|safe`, `Markup(`, `autoescape false`, and JS that writes
   fetched data with `innerHTML`, `outerHTML`, `insertAdjacentHTML` or
   `document.write` instead of `textContent`.
4. **CSRF.** Every `<form method="post">` includes `csrf_token()`. Flag any
   `csrf.exempt` and any state-changing `GET` route.
5. **Security headers and CSP.** The `after_request` hook in `create_app`
   still sets the CSP with no `'unsafe-inline'` or `'unsafe-eval'`, and no
   template has inline `<script>`, `on*=` handlers or `style=` attributes
   (they would be blocked or would need the policy weakened).
6. **Secrets and config.** No hard-coded `SECRET_KEY` or database
   password in code; production config has `DEBUG` off and `Secure`,
   `HttpOnly` and `SameSite` session cookies.
7. **Uploads and request size.** Photo uploads are checked by file
   signature (not extension or `Content-Type`), limited to JPEG/PNG/GIF/WebP,
   and the 2 MB limit applies only to `profile.upload_photo`, set before CSRF
   reads the form.
8. **Redirects.** Any redirect to a `next` or other user-supplied URL is
   checked to be a local path.
9. **Passwords and logging.** Passwords go through Werkzeug hashing, and
   no log call includes a password, password hash, session or full form.
10. **Errors.** No route returns tracebacks or raw exception text to the
    user.
11. **Known gaps.** Note, without treating it as a new finding, that the
    app has no login rate limiting (documented in `CLAUDE.md`).

## Report

Give a short report in this order:

1. **Verdict:** one line, e.g. "Safe to commit" or "Do not commit:
   1 secret staged".
2. **Sensitive data:** staged findings first, then untracked, tracked and
   history. For each: file, line, type, masked value, real or false positive,
   and the fix.
3. **Dependencies:** each vulnerable package with its advisory IDs,
   severity and the version that fixes it, or "none found".
4. **Code:** each issue with `file:line`, severity (high, medium, low), what
   could go wrong and the fix.
5. **Passed checks:** one line listing the areas that came out clean.

Keep it factual: if a part was skipped or failed, say so instead of
reporting it as clean.
