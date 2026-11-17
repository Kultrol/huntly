import { sessionChangeKey } from "./types";

/** Sends an opaque marker so each tab fetches its own session from the API. */
export function announceSessionChange() {
  try {
    localStorage.setItem(sessionChangeKey, crypto.randomUUID());
  } catch {
    // Focus and visibility changes still trigger session checks when storage is unavailable.
  }
}
