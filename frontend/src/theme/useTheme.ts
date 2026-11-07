import { useContext } from "react";
import { ThemeContext } from "./ThemeContext";

/** Reads the current theme and exposes the setter for the saved preference. */
export function useTheme() {
  const theme = useContext(ThemeContext);
  if (theme === null) throw new Error("useTheme must be used inside ThemeProvider.");
  return theme;
}
