import { useEffect, useState } from "react";
import { useAuth } from "@/features/auth/session/useAuth";

const slowStartupMs = 15_000;
const startupTimeoutMs = 120_000;
const retryDelayMs = 3_000;

/** Reuses session restoration so entering an auth route won't start another readiness check. */
export function useHomeStartup() {
  const { status: authStatus, refreshSession } = useAuth();
  const [attempt, setAttempt] = useState(0);
  const [isSlow, setIsSlow] = useState(false);
  const [hasTimedOut, setHasTimedOut] = useState(false);
  const isReady = authStatus === "authenticated" || authStatus === "unauthenticated";

  useEffect(() => {
    if (isReady) return;
    const slowTimer = window.setTimeout(() => setIsSlow(true), slowStartupMs);
    const timeoutTimer = window.setTimeout(() => setHasTimedOut(true), startupTimeoutMs);
    return () => {
      window.clearTimeout(slowTimer);
      window.clearTimeout(timeoutTimer);
    };
  }, [isReady, attempt]);

  useEffect(() => {
    // Retry only settled failures, never interrupt a request that's still waking the server.
    if (authStatus !== "error" || hasTimedOut) return;
    // An interval also survives a fast failure when React batches loading -> error.
    const retryTimer = window.setInterval(() => void refreshSession(), retryDelayMs);
    return () => window.clearInterval(retryTimer);
  }, [authStatus, hasTimedOut, refreshSession]);

  function retry() {
    setIsSlow(false);
    setHasTimedOut(false);
    setAttempt((previous) => previous + 1);
    void refreshSession();
  }

  return {
    status: isReady ? "ready" : hasTimedOut ? "error" : "loading",
    isSlow,
    retry,
  } as const;
}
