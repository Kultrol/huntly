import type { RefObject } from "react";
import { sessionChangeKey } from "./types";

export function bindSessionSync({
  isProviderMounted,
  refreshSession,
  cancelSessionRefresh,
}: {
  isProviderMounted: RefObject<boolean>;
  refreshSession: () => Promise<void>;
  cancelSessionRefresh: () => void;
}) {
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
}
