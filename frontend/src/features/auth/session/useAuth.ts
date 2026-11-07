import { useContext } from "react";
import { AuthContext } from "./AuthContext";

/** Gives pages the shared session state and the actions managed by the provider. */
export function useAuth() {
  const auth = useContext(AuthContext);
  if (auth === null) throw new Error("useAuth must be used inside AuthProvider.");
  return auth;
}
