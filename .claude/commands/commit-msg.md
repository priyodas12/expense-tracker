---
description: Write a short (15-30 word) Conventional Commits message from the staged changes
argument-hint: "[optional hint, e.g. scope or intent]"
allowed-tools: Bash(git diff:*), Bash(git status:*), Bash(git log:*), Bash(git branch:*)
---

Write a short commit message for exactly what is **staged**. Read only the
staged changes. Do not run `git add`, `git commit` or anything else that
changes the repository.

## Staged changes

Branch: !`git branch --show-current`

Staged files:
!`git diff --cached --name-status`

Staged diff:
!`git diff --cached`

## Not staged (names only, for the warning in step 2)

!`git diff --name-only`

Recent commit subjects (style reference):
!`git log --format='%s' -5`

Hint from the user (may be empty): $ARGUMENTS

## Steps

1. **Nothing staged:** if the staged file list is empty, reply with one line
   saying nothing is staged and suggesting `git add <files>`. Stop.
2. **Check the stage matches the work.** Note, in one line after the message:
   - any staged file that also appears in the not-staged list (its staged
     copy is older than the working copy, e.g. staged empty and edited
     later): suggest `git add <file>` again;
   - any other not-staged files: say they are **not** in this commit.
   Do not describe what is in the not-staged files.
3. **Work out the intent** of the staged diff (why, not just which files).
   Use the user's hint if given.
4. **Write the message** in Conventional Commits format:

   ```
   <type>(<scope>): <summary>

   - <point>
   - <point>
   ```

   - **type:** `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `style`,
     `build`, `ci`, `chore` or `revert`.
   - **scope** (optional): e.g. `auth`, `expenses`, `budget`, `profile`, `db`,
     `migrations`, `config`, `security`, `charts`, `export`, `tests`, `docker`.
   - **summary:** imperative ("add", not "added"), lower case, no full stop,
     72 characters or fewer.
   - **body:** 1 to 3 short `-` bullets, wrapped at 72 characters. Mention
     the most important of: a new `_migrate_vN` migration, CSP or security
     header changes, request size or upload changes, dependency version
     changes.
   - **breaking change** (removed route, changed config or default, manual
     migration step): add a one-line `BREAKING CHANGE: ...` footer.
5. **Check the length: 15 to 30 words.** Count the words in the summary line
   (including `type(scope):`) and the bullets. Do not count the `-` bullet
   markers or the `BREAKING CHANGE:` footer. If the total is under 15, add a
   bullet; if over 30, cut the least important detail. Recount until it fits.
6. **Unrelated changes staged together:** still write one message, then add
   one line suggesting how to split the commit.

## Output

1. The commit message in one fenced code block, ready to copy.
2. The warning line(s) from step 2 and the split note from step 6, if any.
3. One line with the command: `git commit -F -` (then paste the message).

Nothing else: no word count, no explanation.
