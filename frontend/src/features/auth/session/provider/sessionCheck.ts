import type { RefObject } from "react";
import { ApiError, getErrorMessage } from "@/api/client";
import { getSession } from "../../api/session";
import {
  initialAuthState,
  type AuthState,
  type SessionCheck,
  type SessionCheckTrigger,
} from "./types";

export function cancelSessionRefresh(activeSessionCheck: RefObject<SessionCheck | null>) {
  // Treat earlier responses as stale even if they arrive after cancellation.
  const canceledCheck = activeSessionCheck.current;
  activeSessionCheck.current = null;
  canceledCheck?.controller.abort();
}

export async function checkSession({
  isProviderMounted,
  activeSessionCheck,
  latestAuthState,
  applyAuthState,
  trigger = "refresh",
}: {
  isProviderMounted: RefObject<boolean>;
  activeSessionCheck: RefObject<SessionCheck | null>;
  latestAuthState: RefObject<AuthState>;
  applyAuthState: (nextAuthState: AuthState) => void;
  trigger?: SessionCheckTrigger;
}) {
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
}

export async function refreshSession({
  isProviderMounted,
  isSessionChangeInProgress,
  shouldRefreshAfterSessionChange,
  checkSession,
  trigger,
}: {
  isProviderMounted: RefObject<boolean>;
  isSessionChangeInProgress: RefObject<boolean>;
  shouldRefreshAfterSessionChange: RefObject<boolean>;
  checkSession: (trigger?: SessionCheckTrigger) => Promise<void>;
  trigger?: SessionCheckTrigger;
}) {
  if (!isProviderMounted.current) return;
  // Wait until the pending change has settled so the check uses the resulting cookie.
  if (isSessionChangeInProgress.current) {
    shouldRefreshAfterSessionChange.current = true;
    return;
  }
  await checkSession(trigger);
}
