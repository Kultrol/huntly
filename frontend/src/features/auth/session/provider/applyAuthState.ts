import type { Dispatch, RefObject, SetStateAction } from "react";
import type { AuthState } from "./types";

export function applyAuthState(
  isProviderMounted: RefObject<boolean>,
  latestAuthState: RefObject<AuthState>,
  setAuthState: Dispatch<SetStateAction<AuthState>>,
  nextAuthState: AuthState,
) {
  if (isProviderMounted.current) {
    latestAuthState.current = nextAuthState;
    setAuthState(nextAuthState);
  }
}
