import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

beforeEach(() => {
  // jsdom does not provide media queries for responsive components.
  vi.stubGlobal("matchMedia", (media: string) => Object.assign(new EventTarget(), {
    media,
    matches: false,
  }));
});

afterEach(() => {
  cleanup();
  // Preferences and session-change markers must start fresh for each test.
  localStorage.clear();
});
