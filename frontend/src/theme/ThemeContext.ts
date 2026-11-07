import { createContext } from "react";

export type ResolvedTheme = "light" | "dark";
/** The saved preference can follow the device, while the rendered theme is light or dark. */
export type Theme = ResolvedTheme | "system";

type ThemeContextValue = {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
};

export const ThemeContext = createContext<ThemeContextValue | null>(null);
