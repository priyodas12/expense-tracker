# Contract: Registration and Profile Forms

## Registration: `POST /auth/register`

Form fields (all trimmed, except the password):

| Field | Required | Rule | Error message |
|---|---|---|---|
| `username` | yes | 3 to 30 of `A-Z a-z 0-9 . _ -`; unique ignoring case | existing message; "Username is already taken." |
| `password` | yes | 8 to 128 characters | existing messages |
| `first_name` | yes | 1 to 100 characters; letters (any language), spaces, hyphens, apostrophes | "First name is required." / "First name must be 100 characters or fewer and use only letters, spaces, hyphens or apostrophes." |
| `last_name` | yes | same as first name | same, with "Last name" |
| `email` | yes | valid format, at most 254 characters, unique ignoring case | "Email is required." / "Email must be a valid address, such as name@example.com." / "Email is already in use." |
| `phone` (labelled "Mobile") | yes | at least 7 digits, at most 20 characters, digits, spaces, `+`, `-`, brackets | "Mobile is required." / existing phone message, reworded to "Mobile" |
| `address` | no | at most 300 characters | existing message |
| `gender` | no | `''`, `Female` or `Male` | "Gender must be Female, Male or left blank." |
| `profession` | no | at most 100 characters | "Profession must be 100 characters or fewer." |
| `csrf_token` | yes | | |

Outcomes:

- **Success**: `users` and `profiles` rows created together; redirect to `/auth/login` with
  "Account created. Please log in." (unchanged).
- **Any error**: no rows created; status 200; the form is shown again with every error as a
  flash message and every value except the password filled back in (FR-011).

## Profile: `POST /profile`

The same fields and rules, minus `username` and `password`. The email may equal the user's own
current email. Success redirects to `/profile` with "Profile saved." (unchanged).

## Pages

- `register.html` gains the seven inputs, in the spec's order, with `autocomplete` values
  `given-name`, `family-name`, `email`, `tel`, `street-address`, `sex`, `organization-title`.
  Gender is a `<select>` with a blank default option, `Female` and `Male`.
- `profile.html` replaces the single name input with first and last name, relabels Phone as
  Mobile, and adds gender and profession.
- Both pages load `static/js/availability.js` and include an `aria-live` message element after
  the username (registration only) and email inputs.
- `privacy.html` section 2 lists the details collected at sign-up and why, and removes "We do not
  ask for or store your email address, name or phone number" (FR-016).
