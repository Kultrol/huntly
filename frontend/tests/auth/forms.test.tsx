import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import AppRoutes from "@/app/AppRoutes";
import AuthProvider from "@/features/auth/session/AuthProvider";
import { ThemeProvider } from "@/theme/ThemeProvider";
import { createDeferredResponse, jsonResponse, mockAuthFetchWithDashboard, signedInSession } from "./fixtures";

const { email: accountEmailAddress, name: accountDisplayName } = signedInSession.user;
const validPassword = "correct password";
const dashboardHeading = "Welcome Kevin";

/** Mount the production form, including the session check that allows guest access. */
function renderGuestRoute(formPath: "/login" | "/register") {
  return render(
    <MemoryRouter initialEntries={[formPath]}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
    { wrapper: ThemeProvider },
  );
}

function expectFieldToDescribeError(input: HTMLInputElement, inlineError: HTMLElement) {
  expect(input.getAttribute("aria-invalid")).toBe("true");
  expect(inlineError.id).not.toBe("");
  expect(input.getAttribute("aria-describedby")?.split(/\s+/)).toContain(inlineError.id);
}

describe("authentication forms", () => {
  let fetchMock: ReturnType<typeof mockAuthFetchWithDashboard>;

  beforeEach(() => {
    fetchMock = mockAuthFetchWithDashboard();
  });

  // Accessible inline errors for malformed email on both auth forms
  it.each([
    { formPath: "/login", submitButtonLabel: "Login" },
    { formPath: "/register", submitButtonLabel: "Create account" },
  ] as const)("shows an inline error for a malformed email on $formPath", async ({ formPath, submitButtonLabel }) => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}, 401));
    renderGuestRoute(formPath);

    const emailInput = await screen.findByLabelText<HTMLInputElement>("Email");
    if (formPath === "/register") {
      fireEvent.change(screen.getByLabelText("Name"), { target: { value: accountDisplayName } });
    }
    fireEvent.change(emailInput, { target: { value: "not-an-email" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: validPassword } });
    // Click the real submit button to exercise the form's validation entry point.
    fireEvent.click(screen.getByRole("button", { name: submitButtonLabel }));

    const inlineError = screen.getByRole("alert");
    expect(inlineError.textContent).toBe("Enter a valid email address.");
    expectFieldToDescribeError(emailInput, inlineError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  // Unicode email domain separators forwarded to the API for normalization
  it.each([
    { formPath: "/login", submitButtonLabel: "Login", domainSeparator: "\u3002", codePoint: "U+3002" },
    { formPath: "/login", submitButtonLabel: "Login", domainSeparator: "\uff0e", codePoint: "U+FF0E" },
    { formPath: "/register", submitButtonLabel: "Create account", domainSeparator: "\uff61", codePoint: "U+FF61" },
  ] as const)("submits an email with a $codePoint domain separator from $formPath", async ({
    formPath, submitButtonLabel, domainSeparator,
  }) => {
    const emailAddress = `kevin@example${domainSeparator}com`;
    const isRegistration = formPath === "/register";
    fetchMock.mockResolvedValueOnce(jsonResponse({}, 401))
      .mockResolvedValueOnce(jsonResponse(signedInSession, isRegistration ? 201 : 200));
    renderGuestRoute(formPath);

    fireEvent.change(await screen.findByLabelText("Email"), { target: { value: emailAddress } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: validPassword } });
    if (isRegistration) {
      fireEvent.change(screen.getByLabelText("Name"), { target: { value: accountDisplayName } });
    }
    fireEvent.click(screen.getByRole("button", { name: submitButtonLabel }));

    // The form accepts these separators and sends the original address for server normalization.
    const [requestUrl, requestOptions] = fetchMock.mock.calls[1];
    expect(requestUrl).toBe(`http://localhost:8000/auth${formPath}`);
    expect(requestOptions?.method).toBe("POST");
    expect(JSON.parse(String(requestOptions?.body))).toMatchObject({ email: emailAddress });
    await screen.findByRole("heading", { name: dashboardHeading });
  });

  // Registration password length and inline error recovery with Unicode input
  it("blocks registration below the password minimum and clears the error after correction", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}, 401))
      .mockResolvedValueOnce(jsonResponse(signedInSession, 201));
    renderGuestRoute("/register");

    const passwordInput = await screen.findByLabelText<HTMLInputElement>("Password");
    const submitButton = screen.getByRole("button", { name: "Create account" });
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: accountDisplayName } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: accountEmailAddress } });
    // Each key emoji counts as one code point, even though its JavaScript string length is two.
    fireEvent.change(passwordInput, { target: { value: "🔑".repeat(11) } });
    fireEvent.click(submitButton);

    const inlineError = screen.getByRole("alert");
    expect(inlineError.textContent).toBe("Password must be at least 12 characters.");
    expectFieldToDescribeError(passwordInput, inlineError);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    fireEvent.change(passwordInput, { target: { value: "🔑".repeat(12) } });
    expect(passwordInput.getAttribute("aria-invalid")).not.toBe("true");
    expect(screen.queryByRole("alert")).toBeNull();
    fireEvent.click(submitButton);

    await screen.findByRole("heading", { name: dashboardHeading });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  // Registration counts the trimmed display name in Unicode code points.
  it("accepts a trimmed name of 255 code points and rejects a longer name", async () => {
    const maxLengthName = "🌻".repeat(255);
    const registeredSession = { ...signedInSession, user: { ...signedInSession.user, name: maxLengthName } };
    fetchMock.mockResolvedValueOnce(jsonResponse({}, 401))
      .mockResolvedValueOnce(jsonResponse(registeredSession, 201));
    renderGuestRoute("/register");

    const displayNameInput = await screen.findByLabelText<HTMLInputElement>("Name");
    const submitButton = screen.getByRole("button", { name: "Create account" });
    // A native maxlength would truncate this name because it counts UTF-16 code units.
    expect(displayNameInput.hasAttribute("maxlength")).toBe(false);
    fireEvent.change(displayNameInput, { target: { value: `${maxLengthName}🌻` } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: accountEmailAddress } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: validPassword } });
    fireEvent.click(submitButton);

    const inlineError = screen.getByRole("alert");
    expect(inlineError.textContent).toBe("Name must be at most 255 characters.");
    expectFieldToDescribeError(displayNameInput, inlineError);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    fireEvent.change(displayNameInput, { target: { value: ` ${maxLengthName} ` } });
    expect(screen.queryByRole("alert")).toBeNull();
    fireEvent.click(submitButton);

    await screen.findByRole("heading", { name: `Welcome ${maxLengthName}` });
    const [requestUrl, requestOptions] = fetchMock.mock.calls[1];
    expect(requestUrl).toBe("http://localhost:8000/auth/register");
    expect(JSON.parse(String(requestOptions?.body))).toMatchObject({ name: maxLengthName });
  });

  // Rejected login with a legacy password and duplicate submission protection on retry
  it("keeps rejected login values and submits one request when the user retries", async () => {
    const pendingLoginRetry = createDeferredResponse();
    const legacyPassword = "legacy";
    fetchMock.mockResolvedValueOnce(jsonResponse({}, 401))
      .mockResolvedValueOnce(jsonResponse({}, 401))
      .mockReturnValueOnce(pendingLoginRetry.promise);
    renderGuestRoute("/login");

    const emailInput = await screen.findByLabelText<HTMLInputElement>("Email");
    const passwordInput = screen.getByLabelText<HTMLInputElement>("Password");
    const loginButton = screen.getByRole<HTMLButtonElement>("button", { name: "Login" });
    fireEvent.change(emailInput, { target: { value: accountEmailAddress } });
    fireEvent.change(passwordInput, { target: { value: legacyPassword } });
    fireEvent.click(loginButton);

    expect((await screen.findByRole("alert")).textContent).toBe("Incorrect email or password.");
    // Login sends a shorter existing password so the server can verify it.
    const [requestUrl, requestOptions] = fetchMock.mock.calls[1];
    expect(requestUrl).toBe("http://localhost:8000/auth/login");
    expect(JSON.parse(String(requestOptions?.body))).toMatchObject({
      email: accountEmailAddress,
      password: legacyPassword,
    });
    expect(emailInput.value).toBe(accountEmailAddress);
    expect(passwordInput.value).toBe(legacyPassword);
    expect(loginButton.disabled).toBe(false);

    fireEvent.change(passwordInput, { target: { value: validPassword } });
    expect(screen.queryByRole("alert")).toBeNull();
    const loginForm = screen.getByRole("form", { name: "Sign in to Huntly" });
    // Both submit events arrive before React renders the pending state.
    await act(async () => {
      fireEvent.submit(loginForm);
      fireEvent.submit(loginForm);
    });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(emailInput.disabled).toBe(true);
    expect(screen.queryByRole("alert")).toBeNull();

    await act(async () => pendingLoginRetry.resolve(jsonResponse(signedInSession)));
    await screen.findByRole("heading", { name: dashboardHeading });
  });

  // Duplicate email feedback, preserved registration values, and successful correction
  it("keeps registration values after an email conflict and accepts a corrected address", async () => {
    const availableEmailAddress = "available@example.com";
    const newAccountSession = {
      ...signedInSession,
      user: { ...signedInSession.user, email: availableEmailAddress },
    };
    fetchMock.mockResolvedValueOnce(jsonResponse({}, 401))
      .mockResolvedValueOnce(jsonResponse({}, 409))
      .mockResolvedValueOnce(jsonResponse(newAccountSession, 201));
    renderGuestRoute("/register");

    const displayNameInput = await screen.findByLabelText<HTMLInputElement>("Name");
    const emailInput = screen.getByLabelText<HTMLInputElement>("Email");
    const passwordInput = screen.getByLabelText<HTMLInputElement>("Password");
    const submitButton = screen.getByRole("button", { name: "Create account" });
    fireEvent.change(displayNameInput, { target: { value: accountDisplayName } });
    fireEvent.change(emailInput, { target: { value: accountEmailAddress } });
    fireEvent.change(passwordInput, { target: { value: validPassword } });
    fireEvent.click(submitButton);

    // A duplicate email is a server error attached to the field the user can fix.
    const inlineError = await screen.findByRole("alert");
    expect(inlineError.textContent).toBe("Email is already registered.");
    expectFieldToDescribeError(emailInput, inlineError);
    expect(displayNameInput.value).toBe(accountDisplayName);
    expect(emailInput.value).toBe(accountEmailAddress);
    expect(passwordInput.value).toBe(validPassword);

    fireEvent.change(emailInput, { target: { value: availableEmailAddress } });
    expect(screen.queryByRole("alert")).toBeNull();
    fireEvent.click(submitButton);

    await screen.findByRole("heading", { name: dashboardHeading });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  // Preservation of unsent sign-in fields during background session checks
  it.each([
    { responseStatus: 401, checkOutcome: "confirms the user is signed out" },
    { responseStatus: 503, checkOutcome: "fails temporarily" },
  ])("keeps a partially entered login form when a focus check $checkOutcome", async ({ responseStatus }) => {
    const focusSessionCheck = createDeferredResponse();
    fetchMock.mockResolvedValueOnce(jsonResponse({}, 401)).mockReturnValueOnce(focusSessionCheck.promise);
    renderGuestRoute("/login");

    const emailInput = await screen.findByLabelText<HTMLInputElement>("Email");
    const draftPassword = "partially entered password";
    fireEvent.change(emailInput, { target: { value: accountEmailAddress } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: draftPassword } });

    // Returning to the tab starts a session check while the form holds unsent input.
    act(() => window.dispatchEvent(new Event("focus")));
    expect(fetchMock.mock.calls.map(([requestUrl]) => requestUrl)).toEqual([
      "http://localhost:8000/auth/me",
      "http://localhost:8000/auth/me",
    ]);
    await act(async () => focusSessionCheck.resolve(jsonResponse({}, responseStatus)));

    expect(screen.getByLabelText<HTMLInputElement>("Email").value).toBe(accountEmailAddress);
    expect(screen.getByLabelText<HTMLInputElement>("Password").value).toBe(draftPassword);
    expect(screen.getByRole("heading", { name: "Sign in to Huntly" })).not.toBeNull();
  });
});
