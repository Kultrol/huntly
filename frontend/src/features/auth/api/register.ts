import { authRequest } from "./request";
import { decodeAuthSession } from "./session";
import type { AuthSession, RegisterInput } from "./types";

/** Creates the account and returns the session the server starts for it. */
export default async function register(
  { name, email, password }: RegisterInput,
  signal?: AbortSignal,
): Promise<AuthSession> {
  const response = await authRequest("/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name,
      email: email.trim(),
      password,
    }),
    signal,
  });
  return decodeAuthSession(response);
}
