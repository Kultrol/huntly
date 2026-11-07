import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ApiError, apiRequest, getErrorMessage } from "@/api/client";
import { login } from "../api/login";
import register from "../api/register";
import { getSession, logout } from "../api/session";
import type { AuthSession, LoginInput, RegisterInput } from "../api/types";
import { AuthContext, type AuthContextValue, type AuthStatus } from "./AuthContext";

type AuthState = {
  status: AuthStatus;
  session: AuthSession | null;
  error: string | null;
};

type SessionCheckTrigger = "refresh" | "protected-401";

type SessionCheck = {
  controller: AbortController;
  trigger: SessionCheckTrigger;
  completion: Promise<void>;
};

const initialAuthState: AuthState = { status: "loading", session: null, error: null };
const sessionChangeKey = "huntly:auth-changed";

/** Sends an opaque marker so each tab fetches its own session from the API. */
function announceSessionChange() {
  try {
    localStorage.setItem(sessionChangeKey, crypto.randomUUID());
  } catch {
    // Focus and visibility changes still trigger session checks when storage is unavailable.
  }
}

/** Shares the account and CSRF token from the same cookie-backed session across routes. */
export default function AuthProvider({ children }: { children: ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>(initialAuthState);
  const [isSessionChangePending, setIsSessionChangePending] = useState(false);
  // Request handlers need the latest auth state before React renders it.
  const latestAuthState = useRef(authState);
  const isProviderMounted = useRef(false);
  const activeSessionCheck = useRef<SessionCheck | null>(null);
  // Guard against overlapping requests before the UI renders the pending state.
  const isSessionChangeInProgress = useRef(false);
  const shouldRefreshAfterSessionChange = useRef(false);

  const cancelSessionRefresh = useCallback(() => {
    // Treat earlier responses as stale even if they arrive after cancellation.
    const canceledCheck = activeSessionCheck.current;
    activeSessionCheck.current = null;
    canceledCheck?.controller.abort();
  }, []);

  const applyAuthState = useCallback((nextAuthState: AuthState) => {
    if (isProviderMounted.current) {
      latestAuthState.current = nextAuthState;
      setAuthState(nextAuthState);
    }
  }, []);

  const checkSession = useCallback(async (trigger: SessionCheckTrigger = "refresh") => {
    if (!isProviderMounted.current) return;
    const previousCheck = activeSessionCheck.current;
    // A read started by another protected 401 already checks this session.
    if (trigger === "protected-401" && previousCheck?.trigger === "protected-401") {
      return previousCheck.completion;
    }
    previousCheck?.controller.abort();
    const checkController = new AbortController();
    const previousAuthState = latestAuthState.current;
    // Checks block routing until auth is resolved. Background errors preserve the last confirmed state.
    const isBlockingSessionCheck =
      previousAuthState.status === "loading" || previousAuthState.status === "error";
    if (isBlockingSessionCheck) applyAuthState(initialAuthState);

    async function readSession() {
      try {
        const session = await getSession(checkController.signal);
        if (activeSessionCheck.current?.controller === checkController) {
          applyAuthState({ status: "authenticated", session, error: null });
        }
      } catch (error) {
        if (activeSessionCheck.current?.controller !== checkController) return;
        if (error instanceof ApiError && error.status === 401) {
          applyAuthState({ status: "unauthenticated", session: null, error: null });
        } else {
          const sessionCheckErrorMessage = getErrorMessage(error);
          applyAuthState(isBlockingSessionCheck
            ? { status: "error", session: null, error: sessionCheckErrorMessage }
            : { ...previousAuthState, error: sessionCheckErrorMessage });
        }
      } finally {
        // An older check can finish after a newer one starts. Keep the newer check.
        if (activeSessionCheck.current?.controller === checkController) {
          activeSessionCheck.current = null;
        }
      }
    }

    const completion = readSession();
    activeSessionCheck.current = { controller: checkController, trigger, completion };
    return completion;
  }, [applyAuthState]);

  const refreshSession = useCallback(async (trigger?: SessionCheckTrigger) => {
    if (!isProviderMounted.current) return;
    // Wait until the pending change has settled so the check uses the resulting cookie.
    if (isSessionChangeInProgress.current) {
      shouldRefreshAfterSessionChange.current = true;
      return;
    }
    await checkSession(trigger);
  }, [checkSession]);

  /** Runs one session change at a time and checks the cookie again when needed. */
  const runSessionChange = useCallback(async (
    sessionChange: () => Promise<AuthSession | null>,
    { recheckOnForbidden = false } = {},
  ) => {
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
  }, [applyAuthState, cancelSessionRefresh, checkSession, refreshSession]);

  const signIn = useCallback(
    (loginInput: LoginInput) => runSessionChange(() => login(loginInput)),
    [runSessionChange],
  );
  const signUp = useCallback(
    (registrationInput: RegisterInput) => runSessionChange(() => register(registrationInput)),
    [runSessionChange],
  );
  const signOut = useCallback(() => runSessionChange(async () => {
    await logout(latestAuthState.current.session?.csrf_token ?? null);
    return null;
  }, { recheckOnForbidden: true }), [runSessionChange]);

  const request = useCallback(async (path: string, options: RequestInit = {}) => {
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
  }, [refreshSession]);

  useEffect(() => {
    isProviderMounted.current = true;
    void refreshSession();
    // Recheck when the user returns or another tab signals a cookie change.
    function refreshSessionWhenVisible() {
      if (document.visibilityState !== "hidden") void refreshSession();
    }
    function handleSessionChangeMarker(event: StorageEvent) {
      if (event.key === sessionChangeKey) void refreshSession();
    }
    window.addEventListener("focus", refreshSessionWhenVisible);
    document.addEventListener("visibilitychange", refreshSessionWhenVisible);
    window.addEventListener("storage", handleSessionChangeMarker);
    return () => {
      isProviderMounted.current = false;
      cancelSessionRefresh();
      window.removeEventListener("focus", refreshSessionWhenVisible);
      document.removeEventListener("visibilitychange", refreshSessionWhenVisible);
      window.removeEventListener("storage", handleSessionChangeMarker);
    };
  }, [cancelSessionRefresh, refreshSession]);

  const authContextValue = useMemo<AuthContextValue>(() => ({
    status: authState.status,
    user: authState.session?.user ?? null,
    csrfToken: authState.session?.csrf_token ?? null,
    error: authState.error,
    isPending: isSessionChangePending,
    signIn, signUp, signOut, refreshSession, request,
  }), [authState, isSessionChangePending, signIn, signUp, signOut, refreshSession, request]);

  return <AuthContext value={authContextValue}>{children}</AuthContext>;
}
