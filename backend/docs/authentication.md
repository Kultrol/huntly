# Authentication and sessions

Huntly authenticates accounts with an email address and password. A successful
registration or login creates a PostgreSQL session and sends its random token in
an HttpOnly cookie. Protected endpoints use that session to identify the owner of
company, contact, tracked-role, and event data.

For general installation and startup, use the [backend README](../README.md).
The [architecture guide](architecture.md) explains how authentication fits into
the rest of the application.

## Configure local authentication

Run the backend using the README's Docker Compose instructions. Before starting,
check these entries in `backend/.env`:

```dotenv
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:4173","http://localhost:8000"]
SESSION_COOKIE_SECURE=false
SESSION_LIFETIME_SECONDS=604800
```

These values support local HTTP development: the frontend uses ports 5173 or
4173, and the API and its interactive documentation use port 8000. Keep existing
database credentials when updating an existing `.env`. Copy `.env.example` only
when creating a new configuration file.

An origin consists of the scheme, hostname, and port. `ALLOWED_ORIGINS` requires
exact HTTP(S) origins without wildcards, credentials, paths, or trailing slashes.
Include the API's own origin to make login work from its Swagger page. Use
`localhost` consistently for the API and frontend; mixing it with `127.0.0.1`
changes the cookie's host and the request's origin.

| Setting | Python settings default | Behavior |
| --- | --- | --- |
| `DATABASE_URL` | Required | PostgreSQL connection used by the application and Alembic. |
| `ALLOWED_ORIGINS` | Required | JSON list of permitted browser origins. Credentialed CORS uses this list, and write requests with an `Origin` header must match it. |
| `SESSION_COOKIE_NAME` | `huntly_session` | Cookie name; accepts letters, digits, underscores, and hyphens. |
| `SESSION_COOKIE_SECURE` | `true` | Restricts the cookie to HTTPS when enabled. Use `false` for local HTTP development. |
| `SESSION_LIFETIME_SECONDS` | `604800` | Absolute lifetime in seconds: 7 days by default, with an allowed range of 300–2592000. |

The Python defaults are defined in [config.py](../app/core/config.py).
[compose.yaml](../compose.yaml) overrides the development backend's secure-cookie
setting with `${SESSION_COOKIE_SECURE:-false}` and forces it to `false` for the
test service. It also passes the development backend's lifetime setting with a
604800-second fallback. When running Python directly, settings read the process
environment and the `.env` file in the working directory; environment variables
take precedence. An older `.env` without `SESSION_COOKIE_SECURE` therefore uses
the Python default of `true` outside Compose.

Use HTTPS and `SESSION_COOKIE_SECURE=true` for an HTTPS deployment. The current
`SameSite=Lax` cookie supports same-site hosting, such as different localhost
ports or HTTPS subdomains under the same site. A frontend and API on unrelated
sites need a separate cookie and CSRF configuration decision; the current cookie
will not accompany cross-site frontend requests.

## Try the API in Swagger

After the backend is ready, open [http://localhost:8000/docs](http://localhost:8000/docs).

1. Expand `POST /auth/register`, select **Try it out**, and supply a display name,
   email address, and a password of 12–128 characters. Alternatively, use
   `POST /auth/login` for an existing account.
2. Execute the request. Registration returns 201; login returns 200. The browser
   stores the session cookie automatically. Copy the returned `csrf_token`.
3. Execute `GET /auth/me` to check the current account. It returns the account
   and the same session's CSRF token. No CSRF header is needed for this GET.
4. For a write such as `POST /companies/`, enter the token in its
   **X-CSRF-Token** header field. Supply a body such as
   `{"name": "Example company"}`; `user_id` can be omitted.
5. To sign out, execute `POST /auth/logout` with the same header. Subsequent
   protected requests return 401 until another login.

The CSRF header appears as optional in the generated documentation because safe
requests and logout without an active session do not require it. An authenticated
POST, PATCH, PUT, or DELETE still rejects a missing or incorrect token with 403.
The cookie comes from registration or login; copying the CSRF token alone does
not authenticate another browser or client. If login returns 403, check that the
origin used to open `/docs` is included in `ALLOWED_ORIGINS`.

## What a request does

A login session and a database session serve different purposes. An
[AuthSession](../app/models/auth_session.py) is a stored login that can survive
many requests. A SQLAlchemy `AsyncSession`, supplied by
[get_db](../app/core/database.py), is the request's connection to database work.
Closing that database session does not sign the user out.

Registration and login follow this sequence:

1. FastAPI validates the JSON body. The request must have
   `Content-Type: application/json`, and any supplied browser origin must be
   allowed.
2. The route opens a transaction. The account service creates credentials or
   verifies the password; the session service creates a fresh login token and its
   stored session row.
3. The transaction commits. Only then does the route send the cookie and the
   public account/CSRF response. A failed commit does not issue a new login cookie.

For a protected request, the authentication dependency hashes the cookie token
and looks up an unexpired session together with its user. On writes it also
checks the browser origin and CSRF header. The dependency finishes its lookup
transaction before returning, so the resource handler can open its own
transaction with `async with db.begin()`.

Routes own transactions and commits. Account and session service methods perform
queries and flush pending writes when needed; they do not commit or open their
own transaction scopes. Password changes lock and reload the user, recheck that
the requesting session is active, verify the current password, update its hash,
and revoke every session in one transaction. Login and logout-all use the same
user-row lock to coordinate with concurrent credential changes.

### Cookie and CSRF token

The cookie contains a random 256-bit session token. It is host-only, has path
`/`, is HttpOnly, and uses `SameSite=Lax`. HttpOnly prevents browser JavaScript
from reading the cookie; the browser sends it with eligible requests. The
database stores its SHA-256 digest, not the raw token.

The separate `csrf_token` is returned in the JSON body. The client sends it in
`X-CSRF-Token` for authenticated writes. The backend derives this value from the
secret session token and stores its digest in the session row. Each login has a
different CSRF token. A token from another login does not satisfy the check, even
when both logins belong to the same account.

The cookie identifies the login. The CSRF header proves the caller obtained the
corresponding token rather than relying only on a cookie sent automatically by
the browser. Origin checks and credentialed CORS restrict browser access to the
configured origins. Command-line clients may omit `Origin`, but authenticated
writes still require both the session cookie and CSRF header.

Private API responses use `Cache-Control: no-store`. Passwords, password hashes,
and session-token hashes are excluded from response schemas. Validation errors
omit input values so a rejected request does not echo submitted passwords.

### Expiry and multiple devices

Sessions have an absolute UTC expiry. Requests do not extend that deadline, and
an expired row grants no access even if the cookie still exists. Creating a
session removes that user's expired session rows.

A successful login replaces the session represented by the browser's previous
cookie, including when switching accounts. Other unexpired sessions remain
active. Use the sessions endpoint to revoke one login, or logout-all to revoke
every login. A successful password change revokes all sessions and requires a
fresh login. Session list entries identify logins by ID and creation/expiry
times; they do not include device or browser names.

## Endpoint reference

All paths are relative to the API origin. Authenticated writes require
`X-CSRF-Token` in addition to the cookie. An omitted body is sufficient for
logout, logout-all, and session deletion.

| Method and path | Input | Success and effect |
| --- | --- | --- |
| `POST /auth/register` | JSON `{name, email, password}` | **201**, account/CSRF response and a new session cookie. Creates the account and session together. |
| `POST /auth/login` | JSON `{email, password}` | **200**, account/CSRF response and a fresh session cookie. Replaces the previous cookie's session after successful verification. |
| `GET /auth/me` | Session cookie | **200**, account/CSRF response for the current session. |
| `POST /auth/logout` | Cookie and CSRF header when the session is active | **204**, revokes this login and clears its cookie. No session, an invalid cookie, or an expired session can be logged out idempotently without a CSRF token; origin checks still apply. |
| `POST /auth/logout-all` | Session cookie and CSRF header | **204**, revokes all sessions belonging to the account and clears this browser's cookie. |
| `GET /auth/sessions` | Session cookie | **200**, array of this account's unexpired sessions, ordered by creation time and ID. |
| `DELETE /auth/sessions/{id}` | Session UUID, cookie, and CSRF header | **204**, revokes the owned session. Also clears the cookie if it is the current login. A foreign or missing session returns 404. |
| `PATCH /auth/password` | JSON `{current_password, new_password}`, cookie, and CSRF header | **204**, replaces the password, revokes all sessions, and clears the cookie. |
| `GET /users/me` | Session cookie | **200**, profile containing `id` and `name`. |
| `PATCH /users/me` | JSON `{name}`, cookie, and CSRF header | **200**, updated `id` and `name`. An omitted name leaves it unchanged; explicit null is invalid. |
| `DELETE /users/me` | Session cookie and CSRF header | **204**, deletes an eligible profile, cascades its sessions, and clears the cookie. |

`GET`, `PATCH`, and `DELETE /users/{id}` provide the same profile operations for
the signed-in user's own UUID. Another user's ID returns 404. There is no user
collection/list endpoint or credential-free public user creation endpoint; use
registration to create an account.

Account/CSRF responses from registration, login, and `GET /auth/me` have this
shape:

```json
{
  "user": {"id": "<user UUID>", "name": "Jane", "email": "jane@example.com"},
  "csrf_token": "<this session's CSRF token>"
}
```

Each entry from `GET /auth/sessions` contains `id`, `created_at`, `expires_at`,
and `current`. The dates include timezone information; `current` is true for the
session making the request. No password or token hashes are returned.

### Inputs and errors

Email addresses must be valid, are trimmed, and are lowercased for registration
and login. Registration display names are trimmed, nonblank, and at most 255
characters. Authentication inputs reject unexpected fields.

New passwords require 12–128 characters. Login and current-password checks accept
1–128 characters so verification does not impose the registration minimum on an
existing password. Whitespace is significant and is preserved. Valid Unicode is
supported; text that cannot be encoded as UTF-8 is rejected with 422 before
hashing or verification. Stored passwords use Argon2id with independent salts.
Unknown emails still undergo password verification, and incorrect passwords and
unknown emails share the response `401 {"detail": "Invalid email or password."}`.

| Status | Meaning |
| --- | --- |
| **401** | Missing, invalid, or expired session on a protected endpoint; invalid login credentials; incorrect current password. |
| **403** | Unapproved browser origin or an origin-less request marked cross-site; missing/incorrect CSRF token on an authenticated write; a create request supplies a conflicting owner ID. |
| **404** | Missing or foreign resource, event parent, session ID, or explicit profile ID. |
| **409** | Registration email is already in use. |
| **415** | Registration or login uses a content type other than `application/json`, after origin checks pass. |
| **422** | Invalid body, UUID, or other request field. Validation responses omit submitted input values. |
| **500** | Storage/internal failure. Profile deletion while the user still owns companies, contacts, or roles currently returns 500 through the existing deletion service. |

A failed profile deletion preserves the account and its sessions. Remove owned
domain records before deleting the profile. This operation does not cascade
company/contact/role deletion.

Resource lists for companies, contacts, and tracked roles always derive their
owner from the session. A supplied query `user_id` does not select another owner.
Create bodies can omit `user_id`; a matching ID is accepted for compatibility,
while a conflicting one returns 403. Individual resources are checked against
the signed-in owner, and events inherit ownership from their parent role. Missing
and foreign records share 404 responses to avoid revealing another user's data.

## Integrate a browser client

Include cookies on every request, including registration and login. The browser
handles the HttpOnly cookie; application code retains the returned CSRF token in
memory.

```javascript
const loginResponse = await fetch(`${apiUrl}/auth/login`, {
  method: "POST",
  credentials: "include",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email, password }),
});
if (!loginResponse.ok) {
  throw new Error(`Login failed: ${loginResponse.status}`);
}
const { user, csrf_token } = await loginResponse.json();
```

Use the returned token for subsequent writes:

```javascript
const companyResponse = await fetch(`${apiUrl}/companies/`, {
  method: "POST",
  credentials: "include",
  headers: {
    "Content-Type": "application/json",
    "X-CSRF-Token": csrf_token,
  },
  body: JSON.stringify({ name: "Example company" }),
});
```

After a page reload, restore identity and CSRF state with `GET /auth/me` and
`credentials: "include"`. A 401 means the client must return to login. After successful logout, logout-all, or password change,
clear the client-side account and CSRF state. Use the newly returned token after
a later login; a previous session's token is no longer valid for it.

The [frontend](../../frontend/README.md#authentication) implements this flow in
its session provider. New protected screens can use the provider's request helper
to send the current session's CSRF token.

## Reading the implementation

| File | Responsibility |
| --- | --- |
| [api/auth.py](../app/api/auth.py) | Auth endpoints, transaction boundaries, HTTP error mapping, and cookie updates after commit. |
| [api/auth_responses.py](../app/api/auth_responses.py) | Cookie settings and public account/session response formatting. |
| [api/user.py](../app/api/user.py) | Current-user profile operations and checks for explicit profile UUIDs. |
| [api/ownership.py](../app/api/ownership.py) | Owner-scoped resource and event checks used by domain endpoints. |
| [services/auth.py](../app/services/auth.py) | Account creation, password verification/changes, and coordinated logout-all. |
| [services/auth_session.py](../app/services/auth_session.py) | Session creation, lookup, expiry filtering, listing, and revocation within the caller's transaction. |
| [core/auth.py](../app/core/auth.py) | Cookie authentication dependency, CSRF header, origin checks, and JSON requirement for login/registration. |
| [core/security.py](../app/core/security.py) | Password hashing/verification, token digests, and CSRF derivation. |
| [core/database.py](../app/core/database.py) | Request-scoped SQLAlchemy database sessions; routes own commits. |
| [models/user.py](../app/models/user.py), [models/auth_session.py](../app/models/auth_session.py) | Stored credentials, user/session relationships, constraints, and session deadlines. |
| [schemas/auth.py](../app/schemas/auth.py), [schemas/resource_requests.py](../app/schemas/resource_requests.py) | Account validation, safe response fields, and HTTP create inputs whose owner comes from the session. |

## Existing accounts

The authentication migration preserves existing users and their owned records.
Users without credentials remain unable to log in until a trusted provisioning
or account-linking process is chosen. Registration creates a new account; a
matching display name never claims an existing user's records. Credential
provisioning/linking has no public endpoint. See
[Working with Alembic](alembic-guide.md) for revision details, review, upgrade,
and guarded downgrade instructions.

## Current scope

Email verification, forgotten-password recovery, MFA, and external identity
providers are not implemented. The application has no login/registration rate
limiter. Public hosting needs shared throttling and request/body limits at the
proxy or gateway in addition to the cookie, CSRF, and ownership checks described
here.

For validation commands and coverage, see the [backend test guide](../tests/README.md).
