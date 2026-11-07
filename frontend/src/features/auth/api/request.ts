import { ApiError, apiRequest } from "@/api/client";

const authFieldLabels = {
  name: "Name",
  email: "Email",
  password: "Password",
  current_password: "Current password",
  new_password: "New password",
};

type AuthFieldName = keyof typeof authFieldLabels;
type AuthFieldErrors = Partial<Record<AuthFieldName, string>>;

/** An auth rejection with field feedback safe for the form to display. */
export class AuthApiError extends ApiError {
  readonly fieldErrors: AuthFieldErrors;

  constructor(status: number, message: string, fieldErrors: AuthFieldErrors) {
    super(status, message);
    this.fieldErrors = fieldErrors;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

async function readValidationError(response: Response): Promise<AuthApiError | undefined> {
  let responseBody: unknown;
  try {
    responseBody = await response.json();
  } catch {
    return undefined;
  }
  if (!isRecord(responseBody) || !Array.isArray(responseBody.detail)) return undefined;

  const labeledFieldMessages: string[] = [];
  const fieldErrors: AuthFieldErrors = {};
  // Only copy recognized field messages. Submitted values can contain passwords.
  for (const issue of responseBody.detail) {
    if (!isRecord(issue) || !Array.isArray(issue.loc) || issue.loc.length !== 2) continue;

    const [location, fieldName] = issue.loc;
    if (location !== "body" || typeof fieldName !== "string" || !Object.hasOwn(authFieldLabels, fieldName)) {
      continue;
    }
    if (typeof issue.msg !== "string") continue;

    const message = issue.msg.replace(/^Value error, /, "").trim().slice(0, 300);
    if (!message) continue;
    const authFieldName = fieldName as AuthFieldName;
    fieldErrors[authFieldName] ??= message;
    labeledFieldMessages.push(`${authFieldLabels[authFieldName]}: ${message}`);
    if (labeledFieldMessages.length === 3) break;
  }

  if (labeledFieldMessages.length > 0) {
    return new AuthApiError(response.status, labeledFieldMessages.join(" "), fieldErrors);
  }
}

async function readAuthError(path: string, response: Response): Promise<ApiError | undefined> {
  if (response.status === 401 && path === "/auth/login") {
    return new ApiError(response.status, "Incorrect email or password.");
  }
  if (response.status === 401 && path === "/auth/me") {
    return new ApiError(response.status, "Your session has expired. Please sign in again.");
  }
  if (response.status === 409 && path === "/auth/register") {
    const message = "Email is already registered.";
    return new AuthApiError(response.status, message, { email: message });
  }
  if (response.status === 422) return readValidationError(response);
}

/** Uses the shared transport with auth-specific error messages and field feedback. */
export function authRequest(path: string, options?: RequestInit): Promise<Response> {
  return apiRequest(path, options, (response) => readAuthError(path, response));
}
