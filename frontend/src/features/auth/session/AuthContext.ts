import { createContext } from "react";
import type { AuthUser, LoginInput, RegisterInput } from "../api/types";

/** Route guards distinguish an unknown session from a confirmed signed-out state. */
export type AuthStatus = "loading" | "authenticated" | "unauthenticated" | "error";

export type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  csrfToken: string | null;
  error: string | null;
  isPending: boolean;
  signIn: (input: LoginInput) => Promise<void>;
  signUp: (input: RegisterInput) => Promise<void>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
  request: (path: string, options?: RequestInit) => Promise<Response>;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
