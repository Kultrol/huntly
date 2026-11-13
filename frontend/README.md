# Huntly frontend

Huntly's React and TypeScript frontend runs on Vite. Sign-in and registration use the API's cookie-backed session.

## Development

Use Node.js 24.15 or later on the Node 24 line. CI uses Node 24, and the test environment requires at least 24.15.

Create `frontend/.env` with `VITE_API_URL=http://localhost:8000`, then run:

```sh
npm ci
npm run dev
```

The API URL is public build-time configuration, not a secret. Restart Vite after changing it. The backend must allow the frontend origin and credentialed requests.

## Project layout

- `src/main.tsx` mounts React. `src/app/` assembles providers, defines routes, and holds standalone pages such as Home and Not Found.
- `src/features/auth/` owns sign-in, registration, and session management. Its `pages/` folder contains the route screens, `components/` contains their shared UI, `api/` holds the auth endpoints and their types, and `session/` holds the provider and hook.
- `src/api/` contains shared HTTP transport and service-wide calls. `src/components/ui/` contains reusable shadcn components, and `src/lib/` holds shared utilities.
- `src/theme/` manages the app-wide theme preference. `src/index.css` defines the light and dark design tokens.
- `tests/` groups tests by the feature or shared system they exercise. Vitest loads `tests/setup.ts` for all suites.

Start a new product feature in `src/features/` and register its pages in `src/app/AppRoutes.tsx`. Keep feature-specific code with its feature and move it to a shared folder when multiple features need it.

## Authentication

The homepage shares the auth layout and waits for the existing session check before showing sign-in and registration links. During a cold start it explains the wait, updates its message after 15 seconds, and retries failed checks every 3 seconds. After 2 minutes it stops automatic retries and offers **Try again**. A pending request is allowed to finish; session requests still have the shared 60-second timeout. Leaving the homepage clears its timers, while `AuthProvider` continues to own session requests. The loader respects reduced-motion preferences and announces status changes.

`AuthProvider` restores the browser session through `GET /auth/me` at startup. Use `useAuth()` under the provider for `user`, `csrfToken`, `status`, `isPending`, and the actions `signIn`, `signUp`, `signOut`, and `refreshSession`. Pages do not set account/token state directly. Successful registration signs the user in.

The provider keeps the account and CSRF token together in memory. The backend owns the HttpOnly session cookie; neither passwords nor auth data are saved in browser storage. Other tabs receive only an opaque session-change marker and retrieve their own account/token from the backend. Focus and visibility changes also revalidate the shared cookie.

`RequireAuth` protects the dashboard, while `GuestOnly` redirects authenticated visitors away from login and registration. Guards wait for the initial session check. A `/auth/me` 401 means signed out; a connection/server failure offers retry. Background failures preserve the last confirmed identity and surface an error. The backend remains responsible for authorizing every protected API request.

For protected API calls, use `request(path, options)` from `useAuth()`. It sends cookies and adds the current CSRF token to writes. A 401 can mean an expired session or incorrect credentials for that action. The provider checks the session before clearing the identity and leaves retrying the write to the caller.

Use exact backend paths, including trailing slashes where required. The client rejects redirects to keep passwords and CSRF headers on the intended request. Requests time out after 60 seconds to allow for backend cold starts. The provider runs one sign-in, registration, or logout request at a time. Session checks started before a session change are canceled. An interrupted check or an uncertain response can trigger a fresh check after the change finishes.

Logout revokes the current session and clears its cookie on the backend. A successful 204 response clears the frontend identity immediately. A logout 403 triggers a session check so a later attempt can use the CSRF token for the cookie the browser now has. A session check that confirms the cookie is missing or expired also clears the identity.

## Verification

```sh
npm test
npm run lint
npm run build
```

Tests exercise the real provider, route guards, forms, and API helpers using simulated backend responses. They cover restoration, anonymous/expired sessions, registration, login, logout, errors and retries, request races, duplicate submissions, cross-tab changes, and safe redirects. They do not replace testing a deployed browser against the deployed backend. CI runs these checks for frontend changes.

## Hosting

Set `VITE_API_URL` before building. The frontend origin must appear in the backend's `ALLOWED_ORIGINS`. The backend uses a host-only, HttpOnly, `SameSite=Lax` cookie. In production, serve both the app and its API requests over HTTPS and set `SESSION_COOKIE_SECURE=true` on the backend.

### Render

The repository's [Render configuration](../render.yaml) describes the existing `huntly-site` static site. The API stays on the existing `huntly` web service. The two `onrender.com` hostnames are separate browser sites, so the frontend build uses `VITE_API_URL=/api` to keep cookie requests on the frontend origin.

Apply the settings to the existing static site. When using a Blueprint, review the plan and confirm it adopts `huntly-site`. When using the Dashboard, copy the build settings and add the following rewrites in order. Keep `https://huntly-site.onrender.com` in the API's allowed origins.

| Source | Destination | Purpose |
| --- | --- | --- |
| `/api/*` | `https://huntly-v4bm.onrender.com/*` | Serve API responses on the frontend origin |
| `/*` | `/index.html` | Open routes such as `/login`, `/register`, and `/dashboard` directly |

Before switching the public build to `/api`, verify the API rewrite returns the backend's status and JSON at `/api/auth/me`. Check that it forwards a login POST and preserves the response's `Set-Cookie` header. Confirm the browser sends that cookie back to `/api/auth/me` and that session responses retain `Cache-Control: no-store`.

On the deployed auth build, open `/register` directly and create a test account. Refresh the dashboard to verify session restoration, sign out, open `/dashboard` directly to verify the guard, and sign in again.
