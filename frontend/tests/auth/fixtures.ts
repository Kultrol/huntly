import { vi } from "vitest";
import type { AuthSession } from "@/features/auth/api/types";

export const signedInSession = {
  user: { id: "user-id", name: "Kevin", email: "kevin@example.com" },
  csrf_token: "csrf-token",
} satisfies AuthSession;

/** Use a real response so tests exercise the same body decoding as the app. */
export function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Hold a response until the test has reproduced the request ordering it needs. */
export function createDeferredResponse() {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((resolveResponse) => {
    resolve = resolveResponse;
  });
  return { promise, resolve };
}

/** Keep the real auth client and replace only its network boundary. */
export function mockApiFetch() {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
