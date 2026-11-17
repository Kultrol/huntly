import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { AuthSession, LoginInput, RegisterInput } from "../api/types";
import { AuthContext, type AuthContextValue } from "./AuthContext";
import { applyAuthState as commitAuthState } from "./provider/applyAuthState";
import { authenticatedRequest } from "./provider/authenticatedRequest";
import { bindSessionSync } from "./provider/bindSessionSync";
import {
  runSessionChange as performSessionChange,
  signIn as startSignIn,
  signOut as startSignOut,
  signUp as startSignUp,
} from "./provider/runSessionChange";
import {
  cancelSessionRefresh as cancelActiveSessionCheck,
  checkSession as readSession,
  refreshSession as refreshAfterPendingChange,
} from "./provider/sessionCheck";
import {
  initialAuthState,
  type AuthState,
  type SessionCheck,
  type SessionCheckTrigger,
} from "./provider/types";

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
    cancelActiveSessionCheck(activeSessionCheck);
  }, []);

  const applyAuthState = useCallback((nextAuthState: AuthState) => {
    commitAuthState(isProviderMounted, latestAuthState, setAuthState, nextAuthState);
  }, []);

  const checkSession = useCallback((trigger?: SessionCheckTrigger) => {
    return readSession({
      isProviderMounted,
      activeSessionCheck,
      latestAuthState,
      applyAuthState,
      trigger,
    });
  }, [applyAuthState]);

  const refreshSession = useCallback((trigger?: SessionCheckTrigger) => {
    return refreshAfterPendingChange({
      isProviderMounted,
      isSessionChangeInProgress,
      shouldRefreshAfterSessionChange,
      checkSession,
      trigger,
    });
  }, [checkSession]);

  const runSessionChange = useCallback((
    sessionChange: () => Promise<AuthSession | null>,
    { recheckOnForbidden = false } = {},
  ) => {
    return performSessionChange({
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
      recheckOnForbidden,
    });
  }, [applyAuthState, cancelSessionRefresh, checkSession, refreshSession]);

  const signIn = useCallback(
    (loginInput: LoginInput) => startSignIn(runSessionChange, loginInput),
    [runSessionChange],
  );
  const signUp = useCallback(
    (registrationInput: RegisterInput) => startSignUp(runSessionChange, registrationInput),
    [runSessionChange],
  );
  const signOut = useCallback(
    () => startSignOut(runSessionChange, latestAuthState),
    [runSessionChange],
  );

  const request = useCallback((path: string, options: RequestInit = {}) => {
    return authenticatedRequest({
      latestAuthState,
      refreshSession,
      path,
      options,
    });
  }, [refreshSession]);

  useEffect(() => bindSessionSync({
    isProviderMounted,
    refreshSession,
    cancelSessionRefresh,
  }), [cancelSessionRefresh, refreshSession]);

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
