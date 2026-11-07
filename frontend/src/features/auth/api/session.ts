import { authRequest } from "./request";
import type { AuthSession } from "./types";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** Validates the account and CSRF token before the provider accepts the session. */
export async function decodeAuthSession(response: Response): Promise<AuthSession> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    // The response body can still be interrupted after the headers arrive.
    if (error instanceof DOMException) {
      if (error.name === "AbortError") throw error;
      if (error.name === "TimeoutError") {
        throw new Error("The server took too long to respond. Please try again.");
      }
    }
    throw new Error("The server returned an invalid session. Please try again.");
  }

  if (
    !isRecord(payload) ||
    typeof payload.csrf_token !== "string" ||
    !payload.csrf_token ||
    !isRecord(payload.user) ||
    typeof payload.user.id !== "string" ||
    !payload.user.id ||
    typeof payload.user.name !== "string" ||
    !(typeof payload.user.email === "string" || payload.user.email === null)
  ) {
    throw new Error("The server returned an invalid session. Please try again.");
  }

  return {
    user: {
      id: payload.user.id,
      name: payload.user.name,
      email: payload.user.email,
    },
    csrf_token: payload.csrf_token,
  };
}

/** Asks the server which account belongs to the browser's current session cookie. */
export async function getSession(signal?: AbortSignal): Promise<AuthSession> {
  return decodeAuthSession(await authRequest("/auth/me", { signal }));
}

/** Revokes the cookie-backed session using the CSRF token for that session. */
export async function logout(
  csrfToken: string | null,
  signal?: AbortSignal,
): Promise<void> {
  const headers = new Headers();
  if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  await authRequest("/auth/logout", { method: "POST", headers, signal });
}
