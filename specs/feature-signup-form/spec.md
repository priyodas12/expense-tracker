# Feature Specification: Personal Details at Sign-Up

**Feature Branch**: `feature/signup-form`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "add signup fields firstname,lastname,email,mobile,address,gender,profession"

**Additional input** (2026-10-27): "username and email if taken should be notified while profile
creation and creation restricted violating this"

## Clarifications

### Session 2026-10-27

- Q: Which personal details must a new user fill in before their account can be created? → A: First name, last name, email and mobile are required; address, gender and profession are optional.
- Q: Can two different accounts use the same email address? → A: No. Each email belongs to at most one account, ignoring letter case.
- Q: Which choices should the gender field offer? → A: Female and Male only. The field stays optional, so it can be left blank.
- Q: Should the user learn a username or email is taken only after submitting, or while filling in the form? → A: Also while filling it in, as soon as they leave the username or email field; the check on submit still applies.
- Q: Where should the limit on early username and email checks be enforced? → A: In the app itself, with the count shared across all app servers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Give personal details when creating an account (Priority: P1)

A new visitor opens the registration page. Alongside the username and password, they enter their
first name, last name, email address, mobile number, address, gender and profession, then create
the account. After logging in for the first time, they find these details already filled in on
their profile and don't have to enter them a second time.

**Why this priority**: this is the whole feature. Capturing the details once, at the moment the
account is created, is the value the user asked for.

**Independent Test**: register a new account with all seven details, log in, open the profile
page and confirm every detail is shown exactly as entered.

**Acceptance Scenarios**:

1. **Given** a visitor on the registration page, **When** they enter a valid username, password
   and all seven personal details and submit, **Then** the account is created, they are sent to
   the login page with a success message, and after logging in their profile shows every detail
   as entered.
2. **Given** a visitor on the registration page, **When** they submit with first name, last
   name, email or mobile left empty, **Then** the account is not created and a message names
   each missing field.
3. **Given** a visitor on the registration page, **When** they fill in only the four required
   details and leave address, gender and profession empty, **Then** the account is created.
4. **Given** a visitor on the registration page, **When** they submit an invalid email address
   or mobile number, **Then** the account is not created and a message explains the expected
   format.
5. **Given** an account that already uses `ana@example.com`, **When** a visitor registers with
   `Ana@Example.com`, **Then** the account is not created and the message says the email is
   already in use.
6. **Given** an existing account with username `ana` and email `ana@example.com`, **When** a
   visitor registers with username `ANA` and email `Ana@Example.com`, **Then** the account is not
   created and both messages are shown together: "Username is already taken." and "Email is
   already in use."
7. **Given** a visitor typing in the registration form, **When** they enter a username that
   another account has and move to the next field, **Then** "Username is already taken." appears
   next to the username field within 1 second, before they submit.
8. **Given** a visitor typing in the registration form, **When** they enter an email no account
   uses and move to the next field, **Then** the field shows it is available.
9. **Given** a visitor whose browser has scripts turned off, **When** they submit a taken
   username, **Then** they get the same message after submitting, and no account is created.
10. **Given** a visitor whose submission was rejected, **When** the registration page is shown
   again, **Then** every value they typed (except the password) is still in the form so they only
   correct the field in error.

---

### User Story 2 - Review and change the details later (Priority: P2)

A registered user opens their profile page and sees the first name, last name, email, mobile,
address, gender and profession they gave at sign-up. They correct any of them and save.

**Why this priority**: details change (a new job, a new address), and details captured at
sign-up are only useful if the user can keep them up to date.

**Independent Test**: log in as a user created through the new registration form, change the
profession and address on the profile page, save, reload and confirm the new values are shown.

**Acceptance Scenarios**:

1. **Given** a logged-in user, **When** they open their profile, **Then** all seven details are
   shown in editable fields, with gender and profession shown as entered at sign-up.
2. **Given** a logged-in user editing their profile, **When** they save a change that breaks the
   same rules as registration (for example an invalid email), **Then** the change is rejected
   with the same message registration would show, and nothing is saved.

---

### User Story 3 - Existing accounts keep working (Priority: P3)

A user who registered before this change logs in as usual. They are not blocked or forced to
fill in the new details, and any name, email, phone and address they had already saved on their
profile is still there.

**Why this priority**: the change must not lock out or lose data for current users, but it adds
no new capability for them.

**Independent Test**: with an account created before the change (with a full name saved on the
profile), log in, add an expense and open the profile page; nothing is lost and no new detail is
demanded.

**Acceptance Scenarios**:

1. **Given** an account created before this change, **When** the user logs in, **Then** they
   reach their expense list as before, with no prompt that blocks them.
2. **Given** an existing profile with a saved full name, email, phone and address, **When** the
   user opens the profile page after the change, **Then** the email, phone and address are
   unchanged and the saved full name is shown as their first and last name.
3. **Given** an existing user with no gender or profession, **When** they open the profile page,
   **Then** those fields are empty and they can fill them in or leave them empty.

---

### Edge Cases

- A visitor registers with an email address that differs from an existing one only in letter
  case (`Ana@Example.com` vs `ana@example.com`): treated as the same address and rejected as
  already in use. The email is stored as typed.
- Two accounts created before this change already share an email on their profiles: both keep
  it, and the duplicates are listed for the operator when the change is installed. Uniqueness is
  enforced from then on, so either user must choose a different email the next time they save
  their profile.
- A name contains spaces, hyphens, apostrophes or non-English letters (`Mary-Jane`, `O'Brien`,
  `José`, `Nguyễn Văn`): accepted.
- An existing saved full name has one word (`Cher`) or more than two (`Ana Maria Silva`): the
  first word becomes the first name and the rest the last name; one word leaves the last name
  empty.
- A visitor doesn't want to state a gender: they leave the field on its blank default, and the
  account is created with no gender.
- A submission sends a gender value other than Female or Male (for example from an edited form):
  rejected with a message listing the allowed choices.
- A visitor enters leading or trailing spaces in any field: they are trimmed before checking and
  saving.
- A visitor fills in every field at its maximum length: the form still submits and saves.
- The username is taken but every other field is valid: the account is not created, the message
  says the username is taken, and the other values stay in the form.
- Two visitors submit the same username or the same email at the same moment: exactly one account
  is created; the other visitor sees the "already taken" or "already in use" message, never an
  error page, and no duplicate account exists.
- The early check is slow or fails (network problem): no message is shown next to the field,
  nothing blocks typing, and the check on submit gives the answer.
- A username shown as available is taken by someone else before the visitor submits: the submit
  is rejected with "Username is already taken." (the check on submit is the one that counts).
- A visitor or script makes more than 20 early checks in a minute: further checks show nothing
  until the minute is over; submitting the form still works and is still fully checked.
- A user changes their email on the profile page to one used by another account: the change is
  rejected with "Email is already in use." (Usernames can't be changed on the profile page.)
- An existing user whose profile has no email or mobile saves a change on the profile page: the
  save is rejected until email and mobile are filled in, because the profile applies the same
  required fields as registration. Logging in and using the app are never blocked.
- A mobile number written with a country code, spaces or brackets (`+44 (0)20 7946 0958`):
  accepted, and stored as entered.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The registration form MUST ask for first name, last name, email address, mobile
  number, address, gender and profession, in addition to the existing username and password.
- **FR-002**: First name, last name, email address and mobile number MUST be required at
  registration. Address, gender and profession MUST be optional and MAY be left empty.
- **FR-003**: First and last name MUST each be 100 characters or fewer and MAY contain letters
  from any language, spaces, hyphens and apostrophes.
- **FR-004**: The email address MUST be a valid address format (such as `name@example.com`) and
  254 characters or fewer.
- **FR-005**: Each email address MUST belong to at most one account, compared ignoring letter
  case. Registration, and a profile change, MUST be rejected with the message "Email is already
  in use." when another account already has that address.
- **FR-005a**: Before an account is created, the system MUST check both the username and the
  email against existing accounts, ignoring letter case. If either is taken, no account MUST be
  created, and the user MUST be told about each one that is taken ("Username is already taken.",
  "Email is already in use."), alongside any other errors in the form.
- **FR-005b**: On the registration form, as soon as the user leaves the username or email field,
  the system MUST tell them next to that field whether the value is already taken, without
  submitting the form. The same applies to the email field on the profile page (the user's own
  current email never counts as taken).
- **FR-005c**: The early check MUST only help; it MUST NOT replace the check on submit. FR-005a
  still decides whether an account is created, and the form MUST still work, with the same
  messages after submitting, when the early check is unavailable or the browser has scripts
  turned off.
- **FR-005d**: The early check MUST reveal only "available" or "taken" for the exact value
  typed, never any other detail of the account that has it. It MUST NOT be checked for a value
  that fails the format rules (FR-003/FR-004 and the username rule); the format message is shown
  instead.
- **FR-005e**: To limit automated probing for registered usernames and emails, the app itself
  MUST allow one visitor (identified by network address) no more than 20 early checks per minute.
  The limit MUST hold across all app servers together, not per server. Further checks in that
  minute show no result, and the visitor still gets the full answer when they submit. The limit
  MUST work in a plain local or test setup without any extra web server in front of the app.
- **FR-006**: The mobile number MUST contain at least 7 digits, be 20 characters or fewer, and use
  only digits, spaces, `+`, `-` and brackets (the same rule the profile page applies to phone
  numbers today).
- **FR-007**: The address MUST be 300 characters or fewer and MAY span several lines.
- **FR-008**: Gender MUST be either empty or one of exactly two choices: Female or Male. Any
  other submitted value MUST be rejected.
- **FR-009**: Profession MUST be free text of 100 characters or fewer.
- **FR-010**: The account and all of its personal details MUST be saved together: if any check
  fails, nothing is saved.
- **FR-011**: When registration is rejected, the system MUST show every error found (not only
  the first) and MUST keep all entered values except the password.
- **FR-012**: Details entered at registration MUST appear on the user's profile page, where the
  user can view and change all seven of them under the same rules as registration.
- **FR-013**: Accounts created before this change MUST keep working without being asked for the
  new details. Their saved email, phone and address MUST be kept, and their saved full name MUST
  be split into first name (first word) and last name (remaining words).
- **FR-014**: A user's personal details MUST be visible only to that user.
- **FR-015**: Personal details MUST NOT be written to application logs.
- **FR-016**: The Privacy Policy page MUST be updated to state that name, email, mobile, address,
  gender and profession are collected at sign-up, why, and that the user can change them on the
  profile page. (It currently says the app does not ask for an email address, name or phone
  number.)

### Key Entities

- **Account**: the login identity. Username and password, unchanged by this feature.
- **Personal details**: belong to exactly one account. First name, last name, email address,
  mobile number, address, gender and profession. Created at registration; edited on the profile
  page. Replaces the single "full name" with separate first and last names, and adds gender and
  profession to the details already kept on the profile (email, phone, address, photo).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can complete the registration form, including all personal details, in
  under 2 minutes.
- **SC-002**: 100% of accounts created through the new form show, on first login, the same
  personal details that were entered at sign-up.
- **SC-003**: 100% of accounts that existed before the change can still log in, and none lose a
  saved email, phone or address.
- **SC-004**: Every invalid submission is rejected with a message that names each field in error,
  and no partial account is ever created.
- **SC-005**: No personal detail of one user can be seen by any other logged-in user.
- **SC-006**: Zero accounts share a username or an email address (ignoring letter case), including
  when two people register with the same details at the same moment.
- **SC-007**: When a visitor leaves the username or email field, 95% of "taken" or "available"
  results appear within 1 second.
- **SC-008**: With several app servers running, a visitor's 21st early check within one minute
  gets no result, whichever server handles it.

## Assumptions

- The existing username and password stay as the login credentials. Email is collected as a
  personal detail, not as a login or password-reset method, and is not verified (no confirmation
  email). Email verification and login by email are out of scope.
- The mobile number is not verified by SMS.
- Gender and profession, like the other personal details, are visible only to the user and are
  not used for analytics, sorting or any other feature.
- "Mobile" on the registration form is the same detail as "Phone" on the current profile page;
  the profile label changes to "Mobile" for consistency.
- The registration form stays a single page.
- The 20-checks-per-minute limit covers only the early username and email check. It is not
  general rate limiting for login or registration, which remains a separate open item in the
  README, though whatever the plan builds here could later be reused for it.
- Visitors behind one shared network address (an office or a mobile carrier) share one limit;
  20 checks per minute is enough for normal use even then, and submitting is never limited.
- Existing users are not prompted or reminded to complete the new details.
- The profile photo is unchanged and is still added from the profile page, not at sign-up.
- The real operator details and legal review of the Privacy Policy remain an open item (listed in
  the README); this feature only updates the section on what information is collected.
