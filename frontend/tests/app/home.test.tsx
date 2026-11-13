import { StrictMode } from "react";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AppRoutes from "@/app/AppRoutes";
import HomePage from "@/app/pages/HomePage";
import AuthProvider from "@/features/auth/session/AuthProvider";
import { ThemeProvider } from "@/theme/ThemeProvider";
import { createDeferredResponse, jsonResponse, mockAuthFetchWithDashboard, signedInSession } from "../auth/fixtures";

function renderHome({ strict = false, routes = false } = {}) {
  const app = (
    <ThemeProvider>
      <MemoryRouter>
        <AuthProvider>{routes ? <AppRoutes /> : <HomePage />}</AuthProvider>
      </MemoryRouter>
    </ThemeProvider>
  );
  return render(strict ? <StrictMode>{app}</StrictMode> : app);
}

async function advanceTime(ms: number) {
  await act(async () => { await vi.advanceTimersByTimeAsync(ms); });
}

describe("homepage startup", () => {
  let authFetch: ReturnType<typeof mockAuthFetchWithDashboard>;

  beforeEach(() => {
    vi.useFakeTimers();
    authFetch = mockAuthFetchWithDashboard();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("explains a slow startup, then opens sign-in without another session check", async () => {
    const initialCheck = createDeferredResponse();
    authFetch.mockReturnValueOnce(initialCheck.promise);
    renderHome({ routes: true });

    expect(screen.getByRole("heading", { name: "Getting Huntly ready" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Why the wait?" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Sign in" })).toBeNull();
    await advanceTime(15_000);
    expect(screen.getByRole("status").textContent).toContain("taking a little longer");
    expect(authFetch).toHaveBeenCalledTimes(1);

    await act(async () => initialCheck.resolve(jsonResponse({}, 401)));
    expect(screen.getByRole("heading", { name: "Welcome to Huntly" })).toBeTruthy();
    const signIn = screen.getByRole("link", { name: "Sign in" });
    expect(signIn.closest("button")).toBeNull();
    expect(screen.getByRole("link", { name: "Create an account" }).getAttribute("href")).toBe("/register");
    fireEvent.click(signIn);
    expect(screen.getByRole("heading", { name: "Sign in to Huntly" })).toBeTruthy();
    expect(document.title).toBe("Sign in | Huntly");
    await advanceTime(120_000);
    expect(authFetch).toHaveBeenCalledTimes(1);
  });

  it("retries temporary failures and a host loading page until the session endpoint responds", async () => {
    authFetch.mockResolvedValueOnce(jsonResponse({}, 503))
      .mockResolvedValueOnce(new Response("<html>Starting up</html>", { status: 200 }))
      .mockResolvedValueOnce(jsonResponse({}, 401));
    renderHome();
    await advanceTime(0);
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
    await advanceTime(3_000);
    await advanceTime(3_000);
    expect(authFetch).toHaveBeenCalledTimes(3);
    expect(screen.getByRole("heading", { name: "Welcome to Huntly" })).toBeTruthy();
    await advanceTime(120_000);
    expect(authFetch).toHaveBeenCalledTimes(3);
  });

  it("stops automatic retries after two minutes and allows a fresh manual attempt", async () => {
    authFetch.mockRejectedValue(new TypeError("Network unavailable"));
    renderHome();
    await advanceTime(0);
    for (let tick = 0; tick < 40; tick += 1) await advanceTime(3_000);
    expect(screen.getByRole("heading", { name: "We couldn’t connect" })).toBeTruthy();
    const attempts = authFetch.mock.calls.length;
    await advanceTime(60_000);
    expect(authFetch).toHaveBeenCalledTimes(attempts);

    const retryCheck = createDeferredResponse();
    authFetch.mockReturnValueOnce(retryCheck.promise);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(screen.getByRole("status").textContent).toContain("Connecting to your workspace");
    await act(async () => retryCheck.resolve(jsonResponse({}, 401)));
    expect(screen.getByRole("link", { name: "Sign in" })).toBeTruthy();
  });

  it("waits for an automatic retry to settle without overlapping requests", async () => {
    const slowRetry = createDeferredResponse();
    authFetch.mockResolvedValueOnce(jsonResponse({}, 503)).mockReturnValueOnce(slowRetry.promise);
    renderHome();
    await advanceTime(0);
    await advanceTime(3_000);
    const retrySignal = authFetch.mock.calls[1]?.[1]?.signal;
    await advanceTime(30_000);
    expect(authFetch).toHaveBeenCalledTimes(2);
    expect(retrySignal?.aborted).toBe(false);
    await act(async () => slowRetry.resolve(jsonResponse({}, 401)));
    expect(screen.getByRole("link", { name: "Sign in" })).toBeTruthy();
  });

  it("bounds a stalled request and ignores its stale response after a manual retry", async () => {
    const stalledCheck = createDeferredResponse();
    const retryCheck = createDeferredResponse();
    authFetch.mockReturnValueOnce(stalledCheck.promise).mockReturnValueOnce(retryCheck.promise);
    renderHome();
    await advanceTime(120_000);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await act(async () => stalledCheck.resolve(jsonResponse(signedInSession)));
    expect(screen.queryByRole("link", { name: "Sign in" })).toBeNull();
    await act(async () => retryCheck.resolve(jsonResponse({}, 401)));
    expect(screen.getByRole("link", { name: "Sign in" })).toBeTruthy();
  });

  it("uses the existing guest guard for a signed-in visitor", async () => {
    authFetch.mockResolvedValueOnce(jsonResponse(signedInSession));
    renderHome({ routes: true });
    await advanceTime(0);
    fireEvent.click(screen.getByRole("link", { name: "Sign in" }));
    await advanceTime(0);
    expect(screen.getByRole("heading", { name: "Welcome Kevin" })).toBeTruthy();
    expect(authFetch).toHaveBeenCalledTimes(1);
  });

  it("cancels scheduled retries when leaving the homepage", async () => {
    authFetch.mockResolvedValue(jsonResponse({}, 503));
    const { unmount } = renderHome();
    await advanceTime(0);
    const attempts = authFetch.mock.calls.length;
    unmount();
    await advanceTime(180_000);
    expect(authFetch).toHaveBeenCalledTimes(attempts);
  });

  it("cleans up Strict Mode requests and restores the page title on unmount", async () => {
    const oldCheck = createDeferredResponse();
    authFetch.mockReturnValueOnce(oldCheck.promise).mockResolvedValueOnce(jsonResponse({}, 401));
    const originalTitle = document.title;
    const { unmount } = renderHome({ strict: true });
    await advanceTime(0);
    expect(authFetch.mock.calls[0]?.[1]?.signal?.aborted).toBe(true);
    expect(screen.getByRole("link", { name: "Sign in" })).toBeTruthy();
    expect(document.title).toBe("Welcome | Huntly");
    await act(async () => oldCheck.resolve(jsonResponse({}, 503)));
    expect(screen.getByRole("link", { name: "Sign in" })).toBeTruthy();
    unmount();
    expect(document.title).toBe(originalTitle);
    await advanceTime(180_000);
    expect(authFetch).toHaveBeenCalledTimes(2);
  });
});
