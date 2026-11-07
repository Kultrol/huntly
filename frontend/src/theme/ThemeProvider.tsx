import { useLayoutEffect, useState, useSyncExternalStore } from "react";
import type { ReactNode } from "react";
import { ThemeContext } from "./ThemeContext";
import type { ResolvedTheme, Theme } from "./ThemeContext";

// Keep these settings in sync with the theme script in index.html.
const storageKey = "huntly-theme";
const darkModeQuery = "(prefers-color-scheme: dark)";

function readTheme(): Theme {
  try {
    const theme = window.localStorage.getItem(storageKey);
    return theme === "light" || theme === "dark" ? theme : "system";
  } catch {
    return "system";
  }
}

function getSystemTheme(): ResolvedTheme {
  return window.matchMedia?.(darkModeQuery).matches ? "dark" : "light";
}

function subscribeToSystemTheme(onChange: () => void) {
  const query = window.matchMedia?.(darkModeQuery);
  query?.addEventListener("change", onChange);
  return () => query?.removeEventListener("change", onChange);
}

/** Resolves the saved preference against the device theme and applies it across the app. */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemePreference] = useState(readTheme);
  const systemTheme = useSyncExternalStore(subscribeToSystemTheme, getSystemTheme);
  const resolvedTheme = theme === "system" ? systemTheme : theme;

  useLayoutEffect(() => {
    // The root class lets portaled shadcn components inherit the same theme.
    document.documentElement.classList.toggle("dark", resolvedTheme === "dark");
  }, [resolvedTheme]);

  function setTheme(theme: Theme) {
    setThemePreference(theme);
    try {
      window.localStorage.setItem(storageKey, theme);
    } catch {
      return;
    }
  }

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
