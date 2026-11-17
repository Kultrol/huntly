import type { RefObject } from "react";
import { ApiError, apiRequest } from "@/api/client";
import type { AuthState, SessionCheckTrigger } from "./types";

export async function authenticatedRequest({
  latestAuthState,
  refreshSession,
  path,
  options = {},
}: {
  latestAuthState: RefObject<AuthState>;
  refreshSession: (trigger: SessionCheckTrigger) => Promise<void>;
  path: string;
  options?: RequestInit;
}) {
  const headers = new Headers(options.headers);
  const method = (options.method ?? "GET").toUpperCase();
  const csrfTokenAtRequestStart = latestAuthState.current.session?.csrf_token;
  if (csrfTokenAtRequestStart && !["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers.set("X-CSRF-Token", csrfTokenAtRequestStart);
  }
  try {
    return await apiRequest(path, { ...options, headers });
  } catch (error) {
    // The token identifies the confirmed session. A background check alone does not change it.
    if (
      error instanceof ApiError &&
      error.status === 401 &&
      csrfTokenAtRequestStart === latestAuthState.current.session?.csrf_token
    ) {
      await refreshSession("protected-401");
    }
    throw error;
  }
}
