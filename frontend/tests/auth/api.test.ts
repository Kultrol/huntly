import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiRequest } from "@/api/client";
import { login } from "@/features/auth/api/login";
import register from "@/features/auth/api/register";
import { AuthApiError, authRequest } from "@/features/auth/api/request";
import { getSession, logout } from "@/features/auth/api/session";
import type { AuthSession } from "@/features/auth/api/types";
import { jsonResponse, mockApiFetch } from "./fixtures";

const sessionWithNullableEmail: AuthSession = {
  user: { id: "user-id", name: "Kevin", email: null },
  csrf_token: "csrf-token",
};

describe("authentication API", () => {
  let fetchMock: ReturnType<typeof mockApiFetch>;

  beforeEach(() => {
    fetchMock = mockApiFetch();
  });

  describe("request contracts", () => {
    const emailAddress = "kevin@example.com";
    const passwordWithSpaces = "  correct password  ";
    const registrationInput = {
      name: "Kevin",
      email: ` ${emailAddress} `,
      password: passwordWithSpaces,
    };
    const expectedLoginBody = { email: emailAddress, password: passwordWithSpaces };

    // Cookie-backed session lookup and response freshness
    it("restores the session using cookies and bypasses cached responses", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse(sessionWithNullableEmail));

      await expect(getSession()).resolves.toEqual(sessionWithNullableEmail);

      const [requestUrl, requestOptions] = fetchMock.mock.calls[0];
      expect(requestUrl).toBe("http://localhost:8000/auth/me");
      expect(requestOptions?.credentials).toBe("include");
      expect(requestOptions?.cache).toBe("no-store");
      expect(new Headers(requestOptions?.headers).get("Accept")).toBe("application/json");
    });

    // Email trimming and password whitespace in login and registration requests
    it.each([
      {
        endpoint: "/auth/login",
        submitCredentials: login,
        expectedRequestBody: expectedLoginBody,
      },
      {
        endpoint: "/auth/register",
        submitCredentials: register,
        expectedRequestBody: { ...expectedLoginBody, name: registrationInput.name },
      },
    ])("trims the email and preserves the password for $endpoint", async ({
      endpoint, submitCredentials, expectedRequestBody,
    }) => {
      fetchMock.mockResolvedValueOnce(jsonResponse(sessionWithNullableEmail));

      // Both callers receive the same input so the login assertion also checks that it omits the name.
      await submitCredentials(registrationInput);

      const [requestUrl, requestOptions] = fetchMock.mock.calls[0];
      expect(requestUrl).toBe(`http://localhost:8000${endpoint}`);
      expect(requestOptions?.method).toBe("POST");
      expect(new Headers(requestOptions?.headers).get("Content-Type")).toBe("application/json");
      expect(JSON.parse(String(requestOptions?.body))).toEqual(expectedRequestBody);
    });

    // CSRF-protected logout with an empty success response
    it("sends the CSRF token on logout and accepts an empty 204 response", async () => {
      fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

      await expect(logout(sessionWithNullableEmail.csrf_token)).resolves.toBeUndefined();

      const [requestUrl, requestOptions] = fetchMock.mock.calls[0];
      expect(requestUrl).toBe("http://localhost:8000/auth/logout");
      expect(requestOptions?.method).toBe("POST");
      expect(requestOptions?.credentials).toBe("include");
      expect(requestOptions?.body).toBeUndefined();
      expect(new Headers(requestOptions?.headers).get("X-CSRF-Token")).toBe(sessionWithNullableEmail.csrf_token);
    });

    // Redirect policy for requests carrying credentials
    it("blocks redirects even when the caller asks to follow them", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse(sessionWithNullableEmail));

      // Following a redirect could send credentials to a different origin.
      await apiRequest("/auth/login", { method: "POST", redirect: "follow" });

      expect(fetchMock.mock.calls[0][1]?.redirect).toBe("error");
    });

    // API path restrictions before fetch
    it.each([
      { description: "an absolute URL", requestPath: "https://example.com" },
      { description: "a protocol-relative URL", requestPath: "//example.com" },
      { description: "a path with a backslash", requestPath: "/\\example.com" },
    ])("rejects $description before sending the request", async ({ requestPath }) => {
      await expect(apiRequest(requestPath)).rejects.toThrow(/path.*backend/i);
      expect(fetchMock).not.toHaveBeenCalled();
    });
  });

  describe("error handling", () => {
    // Safe messages for common authentication failures
    it.each([
      {
        endpoint: "/auth/login",
        statusCode: 401,
        expectedMessage: /^Incorrect email or password\.$/,
        expectedFieldErrors: undefined,
      },
      {
        endpoint: "/auth/register",
        statusCode: 409,
        expectedMessage: /email.*registered/i,
        expectedFieldErrors: { email: "Email is already registered." },
      },
      {
        endpoint: "/auth/logout",
        statusCode: 403,
        expectedMessage: /authorized|session|refresh/i,
        expectedFieldErrors: undefined,
      },
      {
        endpoint: "/auth/login",
        statusCode: 429,
        expectedMessage: /wait|attempts/i,
        expectedFieldErrors: undefined,
      },
      {
        endpoint: "/auth/me",
        statusCode: 503,
        expectedMessage: /server|unavailable|try again/i,
        expectedFieldErrors: undefined,
      },
    ])("reports HTTP $statusCode from $endpoint without showing server diagnostics", async ({
      endpoint, statusCode, expectedMessage, expectedFieldErrors,
    }) => {
      const serverDiagnostic = "Internal diagnostic that should not be displayed";
      fetchMock.mockResolvedValueOnce(jsonResponse({ detail: serverDiagnostic }, statusCode));

      const requestError = await authRequest(endpoint).catch((failure: unknown) => failure);

      expect(requestError).toBeInstanceOf(ApiError);
      expect(requestError).toMatchObject({
        status: statusCode,
        message: expect.stringMatching(expectedMessage),
      });
      if (expectedFieldErrors) {
        expect(requestError).toBeInstanceOf(AuthApiError);
        expect(requestError).toHaveProperty("fieldErrors", expectedFieldErrors);
      } else {
        expect(requestError).not.toHaveProperty("fieldErrors");
      }
      expect(requestError).not.toHaveProperty("message", expect.stringContaining(serverDiagnostic));
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    // Allowed validation fields and protection of submitted values
    it("exposes only recognized body field messages from a 422 response", async () => {
      const submittedPassword = "secret-password";
      const privateErrorContext = "also-secret";
      fetchMock.mockResolvedValueOnce(jsonResponse({
        detail: [
          // Query errors and inherited object keys do not identify editable body fields.
          { loc: ["query", "name"], msg: "Unexpected query error" },
          { loc: ["body", "constructor"], msg: "Unexpected body error" },
          {
            loc: ["body", "password"],
            msg: "String should have at least 12 characters",
            input: submittedPassword,
            ctx: { password: privateErrorContext, min_length: 12 },
          },
          { loc: ["body", "email"], msg: "Value error, Enter a valid email address." },
        ],
      }, 422));

      const requestError = await register({
        name: "Kevin", email: "kevin@example.com", password: submittedPassword,
      }).catch((failure: unknown) => failure);

      expect(requestError).toBeInstanceOf(ApiError);
      expect(requestError).toBeInstanceOf(AuthApiError);
      expect(requestError).toMatchObject({
        message: "Password: String should have at least 12 characters Email: Enter a valid email address.",
        fieldErrors: {
          password: "String should have at least 12 characters",
          email: "Enter a valid email address.",
        },
      });
      const serializedError = JSON.stringify(requestError);
      expect(serializedError).not.toContain(submittedPassword);
      expect(serializedError).not.toContain(privateErrorContext);
    });

    // Validation fallback for unreadable or unsupported error bodies
    it.each([
      { description: "non-JSON", responseBody: "not JSON" },
      {
        description: "limited to unknown fields",
        responseBody: JSON.stringify({
          detail: [{ loc: ["body", "unexpected"], msg: "Internal diagnostic" }],
        }),
      },
    ])("uses a generic 422 message when the body is $description", async ({ responseBody }) => {
      fetchMock.mockResolvedValueOnce(new Response(responseBody, { status: 422 }));

      await expect(authRequest("/auth/register")).rejects.toMatchObject({
        status: 422,
        message: "Please check the information you entered.",
      });
    });

    // Shared transport leaves auth field formatting to the auth feature
    it("keeps validation errors generic for callers outside the auth feature", async () => {
      const validationResponse = jsonResponse({
        detail: [{ loc: ["body", "name"], msg: "Name is invalid." }],
      }, 422);
      const readResponseBody = vi.spyOn(validationResponse, "json");
      fetchMock.mockResolvedValueOnce(validationResponse);

      await expect(apiRequest("/companies/")).rejects.toMatchObject({
        status: 422,
        message: "Please check the information you entered.",
      });
      expect(readResponseBody).not.toHaveBeenCalled();
    });

    // Network failure before the server responds
    it("reports a connection error when fetch fails before any response", async () => {
      fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

      await expect(login({ email: "kevin@example.com", password: "correct password" }))
        .rejects.toThrow(/connection|reach.*server/i);
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    // Caller cancellation on browsers with and without native signal composition
    it.each(["native signal composition", "the compatibility fallback"])(
      "preserves the cancellation reason using %s",
      async (signalSupport) => {
        if (signalSupport === "the compatibility fallback") {
          vi.stubGlobal("AbortSignal", { timeout: AbortSignal.timeout.bind(AbortSignal) });
        }
        const cancellationController = new AbortController();
        const cancellationReason = new DOMException("Session check was superseded.", "AbortError");
        // Leave the request pending until fetch receives the abort.
        fetchMock.mockImplementationOnce((_requestUrl, requestOptions) => {
          return new Promise((_resolveResponse, rejectResponse) => {
            const requestSignal = requestOptions?.signal;
            requestSignal?.addEventListener("abort", () => rejectResponse(requestSignal.reason));
          });
        });

        const pendingSessionRequest = getSession(cancellationController.signal);
        cancellationController.abort(cancellationReason);

        await expect(pendingSessionRequest).rejects.toBe(cancellationReason);
      },
    );

    // The fallback keeps the timeout connected while the body is being read
    it("still times out after receiving session headers when AbortSignal.any is unavailable", async () => {
      const cancellationController = new AbortController();
      const timeoutController = new AbortController();
      const timeoutReason = new DOMException("Body timed out.", "TimeoutError");
      vi.stubGlobal("AbortSignal", { timeout: () => timeoutController.signal });
      const sessionResponse = jsonResponse(sessionWithNullableEmail);
      fetchMock.mockImplementationOnce(async (_requestUrl, requestOptions) => {
        vi.spyOn(sessionResponse, "json").mockImplementationOnce(async () => {
          timeoutController.abort(timeoutReason);
          throw requestOptions?.signal?.reason;
        });
        return sessionResponse;
      });

      await expect(getSession(cancellationController.signal)).rejects.toThrow(/too long|timed out/i);
    });
  });

  describe("session response validation", () => {
    // Session identity and token checks for successful responses
    it.each([
      { description: "an empty session", responseBody: JSON.stringify({}) },
      {
        description: "a missing CSRF token",
        responseBody: JSON.stringify({ user: sessionWithNullableEmail.user }),
      },
      {
        description: "a null CSRF token",
        responseBody: JSON.stringify({ ...sessionWithNullableEmail, csrf_token: null }),
      },
      {
        description: "an empty CSRF token",
        responseBody: JSON.stringify({ ...sessionWithNullableEmail, csrf_token: "" }),
      },
      {
        description: "a non-string user ID",
        responseBody: JSON.stringify({
          ...sessionWithNullableEmail,
          user: { ...sessionWithNullableEmail.user, id: 42 },
        }),
      },
      {
        description: "a non-string email",
        responseBody: JSON.stringify({
          ...sessionWithNullableEmail,
          user: { ...sessionWithNullableEmail.user, email: 42 },
        }),
      },
      { description: "a non-JSON body", responseBody: "not JSON" },
    ])("rejects a 200 response with $description", async ({ responseBody }) => {
      fetchMock.mockResolvedValueOnce(new Response(responseBody, { status: 200 }));

      await expect(getSession()).rejects.toThrow(/invalid.*session/i);
    });

    // Session decoding when the response body stalls
    it("reports a timeout while reading the response body", async () => {
      const sessionResponse = jsonResponse(sessionWithNullableEmail);
      // Headers have arrived, but reading the session body can still time out.
      vi.spyOn(sessionResponse, "json").mockRejectedValueOnce(new DOMException("Body timed out", "TimeoutError"));
      fetchMock.mockResolvedValueOnce(sessionResponse);

      await expect(getSession()).rejects.toThrow(/too long|timed out/i);
    });
  });
});
