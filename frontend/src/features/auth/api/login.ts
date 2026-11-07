import { authRequest } from "./request";
import { decodeAuthSession } from "./session";
import type { AuthSession, LoginInput } from "./types";

/** Signs in with existing credentials and returns the account and CSRF token. */
export async function login(
  { email, password }: LoginInput,
  signal?: AbortSignal,
): Promise<AuthSession> {
  const response = await authRequest("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: email.trim(),
      password,
    }),
    signal,
  });
  return decodeAuthSession(response);
}
