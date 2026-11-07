import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import App from "@/app/App";
import { jsonResponse, mockApiFetch } from "./fixtures";

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

// Production provider wiring and direct sign-in startup on browsers with older abort APIs
it("opens sign-in through the real app when AbortSignal.any is unavailable", async () => {
  const fetchMock = mockApiFetch().mockResolvedValueOnce(jsonResponse({}, 401));
  window.history.replaceState(null, "", "/login");

  // Keep the browser's native AbortSignal instances and hide only the newer static method.
  vi.stubGlobal("AbortSignal", new Proxy(AbortSignal, {
    get(signalClass, property) {
      return property === "any" ? undefined : Reflect.get(signalClass, property);
    },
  }));
  render(<App />);

  await screen.findByRole("heading", { name: "Sign in to Huntly" });
  expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
    "http://localhost:8000/auth/me",
    expect.objectContaining({ credentials: "include" }),
  );
  expect(window.location.pathname).toBe("/login");
});
