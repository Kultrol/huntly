import { render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import App from "@/app/App";
import { jsonResponse, mockApiFetch } from "./fixtures";

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

// Exercise the real app/provider wiring with the supported native browser APIs.
it("opens sign-in through the real app when the session is anonymous", async () => {
  const fetchMock = mockApiFetch().mockResolvedValueOnce(jsonResponse({}, 401));
  window.history.replaceState(null, "", "/login");

  render(<App />);

  await screen.findByRole("heading", { name: "Sign in to Huntly" });
  expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
    "http://localhost:8000/auth/me",
    expect.objectContaining({ credentials: "include" }),
  );
  expect(window.location.pathname).toBe("/login");
});
