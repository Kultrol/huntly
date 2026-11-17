import type { AuthSession } from "../../api/types";
import type { AuthStatus } from "../AuthContext";

export type AuthState = {
  status: AuthStatus;
  session: AuthSession | null;
  error: string | null;
};

export type SessionCheckTrigger = "refresh" | "protected-401";

export type SessionCheck = {
  controller: AbortController;
  trigger: SessionCheckTrigger;
  completion: Promise<void>;
};

export const initialAuthState: AuthState = { status: "loading", session: null, error: null };
export const sessionChangeKey = "huntly:auth-changed";
