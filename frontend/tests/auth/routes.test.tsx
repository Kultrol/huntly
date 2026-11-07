import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Outlet, Route, Routes, useLocation, type InitialEntry } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import AppRoutes from "@/app/AppRoutes";
import { getAuthRedirect } from "@/features/auth/redirect";
import AuthProvider from "@/features/auth/session/AuthProvider";
import { createDeferredResponse, jsonResponse, mockApiFetch, signedInSession } from "./fixtures";

const dashboardHeading = "Welcome Kevin to the dashboard";
const protectedDestination = "/dashboard?tab=events#today";

/** Expose the router's URL and saved destination alongside the real screens. */
function RouteLocationProbe() {
  const { pathname, search, hash, state } = useLocation();
  return (
    <>
      <output data-testid="current-url">{pathname + search + hash}</output>
      <output data-testid="return-destination">{state?.from}</output>
      <Outlet />
    </>
  );
}

function renderAuthRoutes(initialEntry: InitialEntry) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <AuthProvider>
        <Routes>
          <Route element={<RouteLocationProbe />}>
            <Route path="*" element={<AppRoutes />} />
          </Route>
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("authentication routes", () => {
  let fetchMock: ReturnType<typeof mockApiFetch>;

  beforeEach(() => {
    fetchMock = mockApiFetch();
  });

  // Protected URL recovery across the sign-in and registration screens
  it("returns a signed-out visitor to the original dashboard URL after they switch forms and sign in", async () => {
    const initialSessionCheck = createDeferredResponse();
    const initialDocumentTitle = document.title;
    fetchMock.mockReturnValueOnce(initialSessionCheck.promise)
      .mockResolvedValueOnce(jsonResponse(signedInSession));
    renderAuthRoutes(protectedDestination);

    // A direct visit waits for the initial session check before deciding where to go.
    expect(screen.getByText("Loading user information...")).not.toBeNull();
    expect(screen.queryByRole("heading", { name: dashboardHeading })).toBeNull();
    await act(async () => initialSessionCheck.resolve(jsonResponse({}, 401)));

    const initialSignInHeading = await screen.findByRole("heading", { name: "Sign in to Huntly" });
    expect(document.activeElement).toBe(initialSignInHeading);
    expect(document.title).toBe("Sign in | Huntly");
    expect(screen.getByTestId("current-url").textContent).toBe("/login");
    expect(screen.getByTestId("return-destination").textContent).toBe(protectedDestination);

    // Switching between guest screens carries the query and fragment saved by the guard.
    const registrationLink = screen.getByRole("link", { name: "Create an account" });
    registrationLink.focus();
    fireEvent.click(registrationLink);
    const registrationHeading = await screen.findByRole("heading", { name: "Create your account" });
    expect(document.activeElement).toBe(registrationHeading);
    expect(document.title).toBe("Create your account | Huntly");

    fireEvent.click(await screen.findByRole("link", { name: "Sign in" }));
    const returnedSignInHeading = await screen.findByRole("heading", { name: "Sign in to Huntly" });
    expect(document.activeElement).toBe(returnedSignInHeading);
    expect(document.title).toBe("Sign in | Huntly");

    const emailInput = screen.getByLabelText("Email");
    emailInput.focus();
    fireEvent.change(emailInput, { target: { value: signedInSession.user.email } });
    expect(document.activeElement).toBe(emailInput);
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct password" } });
    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await screen.findByRole("heading", { name: dashboardHeading });
    expect(screen.getByTestId("current-url").textContent).toBe(protectedDestination);
    expect(document.title).toBe(initialDocumentTitle);
  });

  // Dashboard entry after session restoration and navigation on logout success or failure
  it("redirects a signed-in visitor to the dashboard and returns to login when logout succeeds", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(signedInSession))
      .mockResolvedValueOnce(jsonResponse({}, 403))
      .mockResolvedValueOnce(jsonResponse(signedInSession))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    renderAuthRoutes({ pathname: "/login", state: { from: protectedDestination } });

    await screen.findByRole("heading", { name: dashboardHeading });
    expect(screen.getByTestId("current-url").textContent).toBe(protectedDestination);
    expect(screen.queryByRole("heading", { name: "Sign in to Huntly" })).toBeNull();

    // A rejected logout leaves the protected screen open. The successful retry ends the session.
    fireEvent.click(screen.getByRole("button", { name: "Logout" }));
    expect((await screen.findByRole("alert")).textContent).not.toBe("");
    expect(screen.getByRole("heading", { name: dashboardHeading })).not.toBeNull();
    expect(fetchMock.mock.calls[2]?.[0]).toBe("http://localhost:8000/auth/me");
    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await screen.findByRole("heading", { name: "Sign in to Huntly" });
    expect(screen.getByTestId("current-url").textContent).toBe("/login");
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  // The 404 recovery action has one keyboard target with link semantics.
  it("renders a home link on an unknown route", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}, 401));
    renderAuthRoutes("/unknown");

    const recoveryLink = await screen.findByRole("link", { name: "Return to Home Page" });
    expect(recoveryLink.getAttribute("href")).toBe("/");
    expect(recoveryLink.closest("button")).toBeNull();
  });
});

describe("post-login redirect validation", () => {
  // Dashboard fallback for missing return paths, external URLs, and guest route loops
  it.each([
    { scenario: "missing state", navigationState: undefined },
    { scenario: "null state", navigationState: null },
    { scenario: "missing return path", navigationState: {} },
    { scenario: "absolute URL", navigationState: { from: "https://example.com" } },
    { scenario: "protocol-relative URL", navigationState: { from: "//example.com" } },
    { scenario: "backslash-prefixed URL", navigationState: { from: "/\\example.com" } },
    { scenario: "login route", navigationState: { from: "/login" } },
    { scenario: "registration route with a query", navigationState: { from: "/register?next=dashboard" } },
    { scenario: "uppercase login route", navigationState: { from: "/LOGIN" } },
    { scenario: "login route with a trailing slash", navigationState: { from: "/login/" } },
    { scenario: "encoded login route", navigationState: { from: "/%6cogin" } },
    { scenario: "script URL", navigationState: { from: "javascript:alert(1)" } },
    { scenario: "non-string return path", navigationState: { from: 42 } },
  ])("falls back to the dashboard for $scenario", ({ navigationState }) => {
    expect(getAuthRedirect(navigationState)).toBe("/dashboard");
  });
});
