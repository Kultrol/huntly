import { StrictMode, useState } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import AuthProvider from "@/features/auth/session/AuthProvider";
import { useAuth } from "@/features/auth/session/useAuth";
import {
  createDeferredResponse,
  jsonResponse,
  mockApiFetch,
  signedInSession,
} from "./fixtures";

const apiOrigin = "http://localhost:8000";
const sessionCheckUrl = `${apiOrigin}/auth/me`;
const otherAccountSession = {
  user: { id: "other-user", name: "Another user", email: null },
  csrf_token: "next-csrf-token",
};

// Drive the provider directly so these tests can observe identity and CSRF updates together.
function SessionProbe() {
  const authSession = useAuth();
  const [actionError, setActionError] = useState("");
  const loginCredentials = { email: signedInSession.user.email, password: "correct password" };

  async function runAuthAction(authAction: () => Promise<unknown>) {
    setActionError("");
    try {
      await authAction();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Action failed.");
    }
  }

  return (
    <>
      <output data-testid="status">{authSession.status}</output>
      <output data-testid="name">{authSession.user?.name ?? "No user"}</output>
      <output data-testid="csrf">{authSession.csrfToken ?? "No token"}</output>
      <output data-testid="pending">{String(authSession.isPending)}</output>
      <output data-testid="session-error">{authSession.error}</output>
      <output data-testid="action-error">{actionError}</output>
      <button onClick={() => void runAuthAction(() => authSession.signIn(loginCredentials))}>Sign in</button>
      <button onClick={() => void runAuthAction(() => authSession.signUp({
        name: signedInSession.user.name,
        ...loginCredentials,
      }))}>
        Register
      </button>
      <button onClick={() => void runAuthAction(authSession.signOut)}>Sign out</button>
      <button onClick={() => void runAuthAction(authSession.refreshSession)}>Retry</button>
      <button onClick={() => void runAuthAction(() => authSession.request("/auth/password", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: "wrong password", new_password: "replacement password" }),
      }))}>
        Change password
      </button>
    </>
  );
}

function renderProvider() {
  render(
    <AuthProvider>
      <SessionProbe />
    </AuthProvider>,
  );
}

function simulateSessionChangeFromAnotherTab() {
  act(() => window.dispatchEvent(new StorageEvent("storage", {
    key: "huntly:auth-changed",
    newValue: "session-changed",
  })));
}

describe("AuthProvider", () => {
  let fetchMock: ReturnType<typeof mockApiFetch>;

  beforeEach(() => {
    fetchMock = mockApiFetch();
  });

  describe("session checks", () => {
    // Account and CSRF token restoration on startup
    it("restores the user and CSRF token from the browser session", async () => {
      const sessionCheck = createDeferredResponse();
      fetchMock.mockReturnValueOnce(sessionCheck.promise);
      renderProvider();

      expect(screen.getByTestId("status").textContent).toBe("loading");
      expect(screen.getByTestId("name").textContent).toBe("No user");

      await act(async () => sessionCheck.resolve(jsonResponse(signedInSession)));

      expect(screen.getByTestId("status").textContent).toBe("authenticated");
      expect(screen.getByTestId("name").textContent).toBe("Kevin");
      expect(screen.getByTestId("csrf").textContent).toBe("csrf-token");
      expect(fetchMock.mock.calls[0][0]).toBe(sessionCheckUrl);
    });

    // A startup 401 with no active session
    it("treats a missing session as signed out", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse({}, 401));
      renderProvider();

      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));
      expect(screen.getByTestId("csrf").textContent).toBe("No token");
      expect(screen.getByTestId("session-error").textContent).toBe("");
    });

    // Startup recovery after network and server failures
    it.each([
      {
        failure: "a network failure",
        initialSessionRequest: () => Promise.reject(new TypeError("Failed to fetch")),
      },
      { failure: "a server error", initialSessionRequest: async () => jsonResponse({}, 503) },
    ])("allows a retry after $failure during startup", async ({ initialSessionRequest }) => {
      fetchMock.mockImplementationOnce(initialSessionRequest).mockResolvedValueOnce(jsonResponse(signedInSession));
      renderProvider();

      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("error"));
      expect(screen.getByTestId("session-error").textContent).not.toBe("");

      fireEvent.click(screen.getByRole("button", { name: "Retry" }));

      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
      expect(screen.getByTestId("session-error").textContent).toBe("");
    });

    // A cross-tab account switch replaces the identity and token
    it("picks up the new user and token after another tab changes the session", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse(signedInSession))
        .mockResolvedValueOnce(jsonResponse(otherAccountSession));
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("name").textContent).toBe("Kevin"));

      simulateSessionChangeFromAnotherTab();

      await waitFor(() => expect(screen.getByTestId("name").textContent).toBe("Another user"));
      expect(screen.getByTestId("csrf").textContent).toBe("next-csrf-token");
    });

    // A focus check detects session expiry
    it("clears an expired session when the tab regains focus", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse(signedInSession))
        .mockResolvedValueOnce(jsonResponse({}, 401));
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

      act(() => window.dispatchEvent(new Event("focus")));

      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));
      expect(screen.getByTestId("csrf").textContent).toBe("No token");
    });

    // A failed focus check leaves the last verified session intact
    it("keeps the current user and token after a temporary background failure", async () => {
      const sessionCheck = createDeferredResponse();
      fetchMock.mockResolvedValueOnce(jsonResponse(signedInSession)).mockReturnValueOnce(sessionCheck.promise);
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

      act(() => window.dispatchEvent(new Event("focus")));
      await act(async () => sessionCheck.resolve(jsonResponse({}, 503)));

      expect(screen.getByTestId("status").textContent).toBe("authenticated");
      expect(screen.getByTestId("name").textContent).toBe("Kevin");
      expect(screen.getByTestId("csrf").textContent).toBe("csrf-token");
      expect(screen.getByTestId("session-error").textContent).not.toBe("");
    });
  });

  describe("account actions", () => {
    // Account and CSRF token from successful sign-in and registration responses
    it.each([
      { action: "Sign in", endpoint: "/auth/login", status: 200 },
      { action: "Register", endpoint: "/auth/register", status: 201 },
    ])("sets both the user and CSRF token after $action succeeds", async ({ action, endpoint, status }) => {
      fetchMock.mockResolvedValueOnce(jsonResponse({}, 401))
        .mockResolvedValueOnce(jsonResponse(signedInSession, status));
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));

      fireEvent.click(screen.getByRole("button", { name: action }));

      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
      expect(screen.getByTestId("name").textContent).toBe("Kevin");
      expect(screen.getByTestId("csrf").textContent).toBe("csrf-token");
      expect(fetchMock).toHaveBeenNthCalledWith(2, `${apiOrigin}${endpoint}`, expect.objectContaining({
        method: "POST",
      }));
    });

    // A pending logout blocks duplicate requests and waits for confirmation
    it("keeps the session while one logout request is pending and clears it on 204", async () => {
      const pendingLogoutResponse = createDeferredResponse();
      fetchMock.mockResolvedValueOnce(jsonResponse(signedInSession))
        .mockReturnValueOnce(pendingLogoutResponse.promise);
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

      const signOutButton = screen.getByRole("button", { name: "Sign out" });
      fireEvent.click(signOutButton);

      expect(screen.getByTestId("pending").textContent).toBe("true");
      expect(screen.getByTestId("name").textContent).toBe("Kevin");
      expect(screen.getByTestId("csrf").textContent).toBe("csrf-token");
      expect(screen.getByTestId("action-error").textContent).toBe("");
      const [requestUrl, requestOptions] = fetchMock.mock.calls[1];
      expect(requestUrl).toBe(`${apiOrigin}/auth/logout`);
      expect(new Headers(requestOptions?.headers).get("X-CSRF-Token")).toBe(signedInSession.csrf_token);

      // A second action reaches the provider while the first request still owns the session change.
      fireEvent.click(signOutButton);
      expect(fetchMock).toHaveBeenCalledTimes(2);

      await act(async () => pendingLogoutResponse.resolve(new Response(null, { status: 204 })));

      expect(screen.getByTestId("pending").textContent).toBe("false");
      expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
      expect(screen.getByTestId("name").textContent).toBe("No user");
      expect(screen.getByTestId("csrf").textContent).toBe("No token");
    });

    // A forbidden logout leaves the current session intact
    it("preserves the session and reports the error when logout is rejected", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse(signedInSession))
        .mockResolvedValueOnce(jsonResponse({}, 403))
        .mockResolvedValueOnce(jsonResponse(signedInSession));
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

      fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

      await waitFor(() => expect(screen.getByTestId("action-error").textContent).not.toBe(""));
      expect(screen.getByTestId("status").textContent).toBe("authenticated");
      expect(screen.getByTestId("name").textContent).toBe("Kevin");
      expect(screen.getByTestId("csrf").textContent).toBe("csrf-token");
    });

    // Reconcile the cookie after a forbidden logout, then use the current token on a manual retry
    it("recovers a stale logout token before enabling another attempt", async () => {
      const recoveryCheck = createDeferredResponse();
      const logoutUrl = `${apiOrigin}/auth/logout`;
      fetchMock.mockResolvedValueOnce(jsonResponse(signedInSession))
        .mockResolvedValueOnce(jsonResponse({}, 403))
        .mockReturnValueOnce(recoveryCheck.promise)
        .mockResolvedValueOnce(new Response(null, { status: 204 }));
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

      const signOutButton = screen.getByRole("button", { name: "Sign out" });
      fireEvent.click(signOutButton);

      await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
      expect(screen.getByTestId("pending").textContent).toBe("true");
      expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get("X-CSRF-Token"))
        .toBe(signedInSession.csrf_token);

      await act(async () => recoveryCheck.resolve(jsonResponse(otherAccountSession)));

      expect(screen.getByTestId("name").textContent).toBe(otherAccountSession.user.name);
      expect(screen.getByTestId("pending").textContent).toBe("false");
      expect(screen.getByTestId("action-error").textContent).not.toBe("");
      expect(fetchMock.mock.calls.map(([requestUrl]) => requestUrl))
        .toEqual([sessionCheckUrl, logoutUrl, sessionCheckUrl]);

      fireEvent.click(signOutButton);

      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));
      expect(fetchMock.mock.calls[3][0]).toBe(logoutUrl);
      expect(new Headers(fetchMock.mock.calls[3][1]?.headers).get("X-CSRF-Token"))
        .toBe(otherAccountSession.csrf_token);
    });

    // Session recovery when registration may have already set the cookie
    it("checks the session after an unreadable registration response", async () => {
      // Registration may have set the cookie before the client failed to read the body.
      fetchMock.mockResolvedValueOnce(jsonResponse({}, 401))
        .mockResolvedValueOnce(new Response("incomplete JSON", { status: 201 }))
        .mockResolvedValueOnce(jsonResponse(signedInSession));
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));

      fireEvent.click(screen.getByRole("button", { name: "Register" }));

      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
      expect(screen.getByTestId("name").textContent).toBe("Kevin");
      expect(fetchMock.mock.calls.map(([requestUrl]) => requestUrl)).toEqual([
        sessionCheckUrl,
        `${apiOrigin}/auth/register`,
        sessionCheckUrl,
      ]);
    });
  });

  describe("overlapping requests", () => {
    // Successful login takes precedence over the startup check
    it("keeps the new login when the initial session check returns late", async () => {
      const initialCheck = createDeferredResponse();
      fetchMock.mockReturnValueOnce(initialCheck.promise).mockResolvedValueOnce(jsonResponse(otherAccountSession));
      renderProvider();

      fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
      await waitFor(() => expect(screen.getByTestId("name").textContent).toBe("Another user"));

      await act(async () => initialCheck.resolve(jsonResponse(signedInSession)));

      expect(screen.getByTestId("name").textContent).toBe("Another user");
      expect(screen.getByTestId("csrf").textContent).toBe("next-csrf-token");
    });

    // Confirmed logout takes precedence over an older focus check
    it("keeps the user signed out when a focus check returns after logout", async () => {
      const focusCheck = createDeferredResponse();
      fetchMock.mockResolvedValueOnce(jsonResponse(signedInSession))
        .mockReturnValueOnce(focusCheck.promise)
        .mockResolvedValueOnce(new Response(null, { status: 204 }));
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

      act(() => window.dispatchEvent(new Event("focus")));
      fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));

      await act(async () => focusCheck.resolve(jsonResponse(signedInSession)));

      expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
      expect(screen.getByTestId("name").textContent).toBe("No user");
      expect(screen.getByTestId("csrf").textContent).toBe("No token");
    });

    // Cross-tab revalidation resumes after a rejected account action
    it.each([
      { action: "Sign in", endpoint: "/auth/login", status: 401, initialSession: null },
      { action: "Sign out", endpoint: "/auth/logout", status: 403, initialSession: signedInSession },
    ])("resumes an interrupted session check after $action fails", async ({ action, endpoint, status, initialSession }) => {
      const interruptedCheck = createDeferredResponse();
      const failedAction = createDeferredResponse();
      fetchMock.mockResolvedValueOnce(initialSession ? jsonResponse(initialSession) : jsonResponse({}, 401))
        .mockReturnValueOnce(interruptedCheck.promise)
        .mockReturnValueOnce(failedAction.promise)
        .mockResolvedValueOnce(jsonResponse(otherAccountSession));
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("status").textContent)
        .toBe(initialSession ? "authenticated" : "unauthenticated"));

      simulateSessionChangeFromAnotherTab();
      fireEvent.click(screen.getByRole("button", { name: action }));

      expect(fetchMock).toHaveBeenCalledTimes(3);
      expect(fetchMock.mock.calls[1][1]?.signal?.aborted).toBe(true);
      await act(async () => failedAction.resolve(jsonResponse({}, status)));

      // A canceled response arriving after recovery must leave the recovered session intact.
      await act(async () => interruptedCheck.resolve(jsonResponse(signedInSession)));

      expect(fetchMock.mock.calls.map(([requestUrl]) => requestUrl)).toEqual([
        sessionCheckUrl,
        sessionCheckUrl,
        `${apiOrigin}${endpoint}`,
        sessionCheckUrl,
      ]);
      expect(screen.getByTestId("name").textContent).toBe("Another user");
      expect(screen.getByTestId("csrf").textContent).toBe("next-csrf-token");
      expect(screen.getByTestId("action-error").textContent).not.toBe("");
    });

    // StrictMode effect replay supersedes the first mount request
    it("ignores a late response from the first StrictMode effect setup", async () => {
      const initialCheck = createDeferredResponse();
      fetchMock.mockReturnValueOnce(initialCheck.promise).mockResolvedValueOnce(jsonResponse(otherAccountSession));
      // StrictMode restarts the mount effect, leaving the original response free to arrive later.
      render(
        <StrictMode>
          <AuthProvider>
            <SessionProbe />
          </AuthProvider>
        </StrictMode>,
      );
      await waitFor(() => expect(screen.getByTestId("name").textContent).toBe("Another user"));

      await act(async () => initialCheck.resolve(jsonResponse(signedInSession)));

      expect(screen.getByTestId("name").textContent).toBe("Another user");
    });
  });

  describe("protected writes", () => {
    // A session check distinguishes expiry from invalid current credentials
    it.each([
      { result: "expired", checkedSession: null, expectedStatus: "unauthenticated", expectedName: "No user" },
      { result: "active", checkedSession: signedInSession, expectedStatus: "authenticated", expectedName: "Kevin" },
    ])("uses a session check to handle a 401 when the session is $result", async ({
      checkedSession,
      expectedStatus,
      expectedName,
    }) => {
      fetchMock.mockResolvedValueOnce(jsonResponse(signedInSession))
        .mockResolvedValueOnce(jsonResponse({}, 401))
        .mockResolvedValueOnce(checkedSession ? jsonResponse(checkedSession) : jsonResponse({}, 401));
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

      fireEvent.click(screen.getByRole("button", { name: "Change password" }));

      await waitFor(() => expect(screen.getByTestId("action-error").textContent).not.toBe(""));
      expect(screen.getByTestId("status").textContent).toBe(expectedStatus);
      expect(screen.getByTestId("name").textContent).toBe(expectedName);
      expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get("X-CSRF-Token")).toBe("csrf-token");
      expect(fetchMock.mock.calls.map(([requestUrl]) => requestUrl)).toEqual([
        sessionCheckUrl,
        `${apiOrigin}/auth/password`,
        sessionCheckUrl,
      ]);
    });

    // A failed background check leaves a protected 401 relevant to the current session
    it("checks a rejected write even when an overlapping focus check failed", async () => {
      const pendingWrite = createDeferredResponse();
      fetchMock.mockResolvedValueOnce(jsonResponse(signedInSession))
        .mockReturnValueOnce(pendingWrite.promise)
        .mockResolvedValueOnce(jsonResponse({}, 503))
        .mockResolvedValueOnce(jsonResponse({}, 401));
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

      fireEvent.click(screen.getByRole("button", { name: "Change password" }));
      act(() => window.dispatchEvent(new Event("focus")));
      await waitFor(() => expect(screen.getByTestId("session-error").textContent).not.toBe(""));

      await act(async () => pendingWrite.resolve(jsonResponse({}, 401)));

      expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
      expect(fetchMock.mock.calls.map(([requestUrl]) => requestUrl)).toEqual([
        sessionCheckUrl,
        `${apiOrigin}/auth/password`,
        sessionCheckUrl,
        sessionCheckUrl,
      ]);
    });

    // A late 401 belongs to the session that sent the write
    it("keeps a newer confirmed session when an older write is rejected", async () => {
      const pendingWrite = createDeferredResponse();
      fetchMock.mockResolvedValueOnce(jsonResponse(signedInSession))
        .mockReturnValueOnce(pendingWrite.promise)
        .mockResolvedValueOnce(jsonResponse(otherAccountSession));
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

      fireEvent.click(screen.getByRole("button", { name: "Change password" }));
      simulateSessionChangeFromAnotherTab();
      await waitFor(() => expect(screen.getByTestId("name").textContent).toBe(otherAccountSession.user.name));

      await act(async () => pendingWrite.resolve(jsonResponse({}, 401)));

      expect(fetchMock).toHaveBeenCalledTimes(3);
      expect(screen.getByTestId("status").textContent).toBe("authenticated");
      expect(screen.getByTestId("csrf").textContent).toBe(otherAccountSession.csrf_token);
    });

    // Concurrent 401s for the same session share one recovery check
    it("shares an in-flight recovery check across rejected writes", async () => {
      const firstWrite = createDeferredResponse();
      const secondWrite = createDeferredResponse();
      const recoveryCheck = createDeferredResponse();
      fetchMock.mockResolvedValueOnce(jsonResponse(signedInSession))
        .mockReturnValueOnce(firstWrite.promise)
        .mockReturnValueOnce(secondWrite.promise)
        .mockReturnValueOnce(recoveryCheck.promise);
      renderProvider();
      await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

      const changePasswordButton = screen.getByRole("button", { name: "Change password" });
      fireEvent.click(changePasswordButton);
      fireEvent.click(changePasswordButton);
      await act(async () => firstWrite.resolve(jsonResponse({}, 401)));
      await act(async () => secondWrite.resolve(jsonResponse({}, 401)));

      expect(fetchMock).toHaveBeenCalledTimes(4);
      const [requestUrl, requestOptions] = fetchMock.mock.calls[3];
      expect(requestUrl).toBe(sessionCheckUrl);
      expect(requestOptions?.signal?.aborted).toBe(false);

      await act(async () => recoveryCheck.resolve(jsonResponse({}, 401)));

      expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
      expect(screen.getByTestId("action-error").textContent).not.toBe("");
    });
  });
});
