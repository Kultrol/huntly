import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  // Preferences and session-change markers must start fresh for each test.
  localStorage.clear();
});
