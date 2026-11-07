import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ResolvedTheme, Theme } from "@/theme/ThemeContext";
import { ThemeProvider } from "@/theme/ThemeProvider";
import { useTheme } from "@/theme/useTheme";

const themeStorageKey = "huntly-theme";

/** Simulates the browser media query and the change event the provider listens for. */
function mockDeviceColorScheme(initialDeviceTheme: ResolvedTheme) {
  const colorSchemeQuery = Object.assign(new EventTarget(), {
    media: "(prefers-color-scheme: dark)",
    matches: initialDeviceTheme === "dark",
  });
  vi.stubGlobal("matchMedia", (requestedQuery: string) => {
    expect(requestedQuery).toBe(colorSchemeQuery.media);
    return colorSchemeQuery;
  });

  return function setDeviceTheme(nextDeviceTheme: ResolvedTheme) {
    act(() => {
      colorSchemeQuery.matches = nextDeviceTheme === "dark";
      colorSchemeQuery.dispatchEvent(Object.assign(new Event("change"), {
        matches: colorSchemeQuery.matches,
      }));
    });
  };
}

/** Checks the hook state and the root class used by components to style the page. */
function expectAppliedTheme(
  currentTheme: ReturnType<typeof useTheme>,
  expectedPreference: Theme,
  expectedResolvedTheme: ResolvedTheme,
) {
  expect(currentTheme).toMatchObject({
    theme: expectedPreference,
    resolvedTheme: expectedResolvedTheme,
  });
  expect(document.documentElement.classList.contains("dark")).toBe(expectedResolvedTheme === "dark");
}

describe("theme preferences", () => {
  afterEach(() => {
    // The provider applies the theme outside the rendered React tree.
    document.documentElement.classList.remove("dark");
  });

  // Persistence and restoration of a manually selected theme
  it("saves an explicit theme and applies it again after remounting", () => {
    mockDeviceColorScheme("light");
    const initialMount = renderHook(useTheme, { wrapper: ThemeProvider });

    act(() => initialMount.result.current.setTheme("dark"));

    expectAppliedTheme(initialMount.result.current, "dark", "dark");
    expect(localStorage.getItem(themeStorageKey)).toBe("dark");

    // Simulate a fresh page while keeping the saved preference in storage.
    initialMount.unmount();
    document.documentElement.classList.remove("dark");

    const { result: restoredTheme } = renderHook(useTheme, { wrapper: ThemeProvider });

    expectAppliedTheme(restoredTheme.current, "dark", "dark");
  });

  // Live device theme updates and precedence of a manual override
  it("follows device changes while the system preference is selected", () => {
    const setDeviceTheme = mockDeviceColorScheme("dark");
    const { result: activeTheme } = renderHook(useTheme, { wrapper: ThemeProvider });

    expectAppliedTheme(activeTheme.current, "system", "dark");
    setDeviceTheme("light");
    expectAppliedTheme(activeTheme.current, "system", "light");

    // A manual preference takes precedence even when the device changes again.
    act(() => activeTheme.current.setTheme("light"));
    setDeviceTheme("dark");
    expectAppliedTheme(activeTheme.current, "light", "light");

    // Returning to system applies the current device theme right away.
    act(() => activeTheme.current.setTheme("system"));
    expectAppliedTheme(activeTheme.current, "system", "dark");
  });

  // Device theme fallback for an unrecognized saved preference
  it("uses the device theme when the saved preference is unrecognized", () => {
    mockDeviceColorScheme("dark");
    localStorage.setItem(themeStorageKey, "unsupported-theme");

    const { result: restoredTheme } = renderHook(useTheme, { wrapper: ThemeProvider });

    expectAppliedTheme(restoredTheme.current, "system", "dark");
  });

  // Theme changes within the current page when browser storage is blocked
  it("allows an in-memory theme choice when browser storage is blocked", () => {
    mockDeviceColorScheme("light");
    function rejectStorageAccess(): never {
      throw new DOMException("Storage is blocked.", "SecurityError");
    }
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(rejectStorageAccess);
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(rejectStorageAccess);

    // Reading the preference can fail on mount and writing it can fail after a choice.
    const { result: activeTheme } = renderHook(useTheme, { wrapper: ThemeProvider });
    expectAppliedTheme(activeTheme.current, "system", "light");

    act(() => activeTheme.current.setTheme("dark"));
    expectAppliedTheme(activeTheme.current, "dark", "dark");
  });
});
