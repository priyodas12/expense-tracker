# Contract: Early Username and Email Check

Used by `static/js/availability.js` on the registration and profile pages (FR-005b to FR-005e).

## Request

`POST /auth/check-availability`

Form-encoded body:

| Field | Required | Values |
|---|---|---|
| `field` | yes | `username` or `email` |
| `value` | yes | The text typed, trimmed by the server |
| `csrf_token` | yes (outside the testing config) | The page's CSRF token |

Login is not required. When the visitor is logged in and `field` is `email`, their own current
email counts as available.

## Responses

All responses are JSON with `Content-Type: application/json` and `Cache-Control: no-store`.

| Status | Body | Meaning |
|---|---|---|
| 200 | `{"field": "username", "status": "available"}` | No account has this value |
| 200 | `{"field": "username", "status": "taken"}` | Another account has it, ignoring letter case |
| 200 | `{"field": "email", "status": "invalid"}` | The value fails the format rule, so it wasn't looked up (FR-005d) |
| 429 | `{"field": "email", "status": "limited"}` | More than 20 checks from this visitor in the current minute (FR-005e) |
| 400 | `{"status": "bad_request"}` | `field` missing or not `username`/`email`, or a missing or invalid CSRF token |

Rules:

- The body never contains anything about the account that has the value: no id, username,
  name or date (FR-005d).
- Every request counts toward the limit, including `invalid` and `bad_request` ones, except a
  request rejected by CSRF.
- Neither the value nor the result is written to application logs (FR-015).
- The answer is advice only. Registration and profile saves check again (FR-005c).

## Browser behaviour

- Runs on the `change` event of the username and email inputs, not on every keystroke.
- `available`: shows "Available" next to the field. `taken`: shows "Username is already taken."
  or "Email is already in use.". `invalid`, `limited`, an error or no answer: shows nothing.
- Writes messages with `textContent` into an element with `aria-live="polite"`.
- Never disables the submit button or blocks typing.
