const configuredUrl: unknown = import.meta.env.VITE_API_URL;

if (typeof configuredUrl !== "string" || !configuredUrl.trim()) {
  throw new Error("Set VITE_API_URL to the backend URL before starting the app.");
}

export const API_URL = configuredUrl.trim().replace(/\/+$/, "");

/** An HTTP rejection from the API. Feature clients can add their own error details. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type ReadApiError = (response: Response) => Promise<ApiError | undefined>;

function getHttpErrorMessage(status: number): string {
  if (status >= 500) {
    return "The server is unavailable. Please try again shortly.";
  }
  if (status === 401) {
    return "This request requires authentication or valid credentials.";
  }
  if (status === 403) {
    return "This request could not be authorized. Refresh your session and try again.";
  }
  if (status === 429) {
    return "Too many attempts. Please wait before trying again.";
  }
  if (status === 422) {
    return "Please check the information you entered.";
  }
  return "The request failed. Please try again.";
}

function combineRequestSignals(requestSignal: AbortSignal, timeoutSignal: AbortSignal): AbortSignal {
  if (typeof AbortSignal.any === "function") {
    return AbortSignal.any([requestSignal, timeoutSignal]);
  }
  if (requestSignal.aborted) return requestSignal;
  if (timeoutSignal.aborted) return timeoutSignal;

  const controller = new AbortController();
  function forwardAbort(event: Event) {
    const sourceSignal = event.currentTarget === requestSignal ? requestSignal : timeoutSignal;
    requestSignal.removeEventListener("abort", forwardAbort);
    timeoutSignal.removeEventListener("abort", forwardAbort);
    controller.abort(sourceSignal.reason);
  }
  // Keep forwarding after the headers arrive since the response body can still be pending.
  requestSignal.addEventListener("abort", forwardAbort);
  timeoutSignal.addEventListener("abort", forwardAbort);
  return controller.signal;
}

/** Sends a cookie-backed request and gives callers consistent HTTP and network errors. */
export async function apiRequest(
  path: string,
  options: RequestInit = {},
  readError?: ReadApiError,
): Promise<Response> {
  if (!path.startsWith("/") || path.startsWith("//") || path.includes("\\")) {
    throw new Error("API requests must use a path within the configured backend.");
  }

  const headers = new Headers(options.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  const timeoutSignal = AbortSignal.timeout(60_000);
  // Let callers cancel superseded requests while keeping the shared timeout.
  const signal = options.signal
    ? combineRequestSignals(options.signal, timeoutSignal)
    : timeoutSignal;

  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      credentials: "include",
      cache: "no-store",
      // Following a redirect could forward a password or CSRF header to another origin.
      redirect: "error",
      headers,
      signal,
    });
    if (!response.ok) {
      const featureError = await readError?.(response);
      throw featureError ?? new ApiError(response.status, getHttpErrorMessage(response.status));
    }
    return response;
  } catch (error) {
    // Preserve cancellation so a superseded session check can exit quietly.
    if (options.signal?.aborted) throw options.signal.reason;
    if (timeoutSignal.aborted) {
      throw new Error("The server took too long to respond. Please try again.");
    }
    if (error instanceof ApiError) throw error;
    throw new Error("Unable to reach the server. Check your connection and try again.");
  }
}

export function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}
