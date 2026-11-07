const defaultAuthDestination = "/dashboard";

/** Reads the return path saved by the route guard and falls back to the dashboard. */
export function getAuthRedirect(state: unknown): string {
  if (!state || typeof state !== "object" || !("from" in state)) {
    return defaultAuthDestination;
  }

  const returnPath = state.from;
  if (
    typeof returnPath !== "string" ||
    !returnPath.startsWith("/") ||
    returnPath.startsWith("//") ||
    returnPath.includes("\\") ||
    [...returnPath].some((character) => character.charCodeAt(0) <= 32)
  ) {
    return defaultAuthDestination;
  }

  try {
    // Decode the path to catch encoded links back to login or registration.
    const pathname = new URL(returnPath, "https://huntly.invalid").pathname;
    const normalizedPathname = decodeURIComponent(pathname).replace(/\/+$/, "").toLowerCase();
    if (
      normalizedPathname === "/login" ||
      normalizedPathname === "/register" ||
      normalizedPathname.startsWith("//") ||
      normalizedPathname.includes("\\")
    ) {
      return defaultAuthDestination;
    }
  } catch {
    return defaultAuthDestination;
  }

  return returnPath;
}
