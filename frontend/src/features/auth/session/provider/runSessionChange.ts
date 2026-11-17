import type { RefObject } from "react";
import { ApiError } from "@/api/client";
import { login } from "../../api/login";
import register from "../../api/register";
import { logout } from "../../api/session";
import type { AuthSession, LoginInput, RegisterInput } from "../../api/types";
import { announceSessionChange } from "./announceSessionChange";
import type { AuthState, SessionCheck } from "./types";

type RunSessionChange = (
  sessionChange: () => Promise<AuthSession | null>,
  options?: { recheckOnForbidden?: boolean },
) => Promise<void>;

/** Runs one session change at a time and checks the cookie again when needed. */
export async function runSessionChange({
  isSessionChangeInProgress,
  activeSessionCheck,
  isProviderMounted,
  latestAuthState,
  shouldRefreshAfterSessionChange,
  setIsSessionChangePending,
  cancelSessionRefresh,
  applyAuthState,
  checkSession,
  refreshSession,
  sessionChange,
  recheckOnForbidden = false,
}: {
  isSessionChangeInProgress: RefObject<boolean>;
  activeSessionCheck: RefObject<SessionCheck | null>;
  isProviderMounted: RefObject<boolean>;
  latestAuthState: RefObject<AuthState>;
  shouldRefreshAfterSessionChange: RefObject<boolean>;
  setIsSessionChangePending: (pending: boolean) => void;
  cancelSessionRefresh: () => void;
  applyAuthState: (nextAuthState: AuthState) => void;
  checkSession: () => Promise<void>;
  refreshSession: () => Promise<void>;
  sessionChange: () => Promise<AuthSession | null>;
  recheckOnForbidden?: boolean;
}) {
  if (isSessionChangeInProgress.current) {
    throw new Error("Another authentication request is already in progress.");
  }
  isSessionChangeInProgress.current = true;
  setIsSessionChangePending(true);
  // Remember the canceled check in case the write fails to establish a new session state.
  const hadInFlightSessionRefresh = activeSessionCheck.current !== null;
  cancelSessionRefresh();
  try {
    const session = await sessionChange();
    applyAuthState({ status: session ? "authenticated" : "unauthenticated", session, error: null });
    announceSessionChange();
  } catch (error) {
    if (recheckOnForbidden && error instanceof ApiError && error.status === 403) {
      // The cookie may now require a different CSRF token. Keep logout pending
      // while this read reconciles the session and covers any already queued checks.
      shouldRefreshAfterSessionChange.current = false;
      await checkSession();
    } else {
      // A canceled check may have been triggered by another tab. A lost response
      // can also leave the cookie changed. In either case, recheck via GET /auth/me.
      const hasUncertainOutcome = !(error instanceof ApiError);
      if (hadInFlightSessionRefresh || hasUncertainOutcome) {
        shouldRefreshAfterSessionChange.current = true;
      }
      if (hasUncertainOutcome) announceSessionChange();
    }
    throw error;
  } finally {
    isSessionChangeInProgress.current = false;
    if (isProviderMounted.current) setIsSessionChangePending(false);
    // Coalesce queued checks into a single read after the change.
    if (shouldRefreshAfterSessionChange.current || latestAuthState.current.status === "loading") {
      shouldRefreshAfterSessionChange.current = false;
      void refreshSession();
    }
  }
}

export function signIn(runSessionChange: RunSessionChange, loginInput: LoginInput) {
  return runSessionChange(() => login(loginInput));
}

export function signUp(runSessionChange: RunSessionChange, registrationInput: RegisterInput) {
  return runSessionChange(() => register(registrationInput));
}

export function signOut(
  runSessionChange: RunSessionChange,
  latestAuthState: RefObject<AuthState>,
) {
  return runSessionChange(async () => {
    await logout(latestAuthState.current.session?.csrf_token ?? null);
    return null;
  }, { recheckOnForbidden: true });
}
