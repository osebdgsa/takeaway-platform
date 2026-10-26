const TOKEN_KEY = "takeaway.token";
const REFRESH_KEY = "takeaway.refresh";

// sessionStorage, not localStorage: the tokens do not survive a closed tab,
// so stolen tokens have a smaller window. Authorisation is still enforced
// server-side; the SPA never gates on the token itself.
export function getToken(): string | null {
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    window.sessionStorage.setItem(TOKEN_KEY, token);
  } else {
    window.sessionStorage.removeItem(TOKEN_KEY);
  }
}

export function getRefreshToken(): string | null {
  return window.sessionStorage.getItem(REFRESH_KEY);
}

export function setTokens(tokens: { access_token: string; refresh_token: string } | null): void {
  if (tokens) {
    window.sessionStorage.setItem(TOKEN_KEY, tokens.access_token);
    window.sessionStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  } else {
    window.sessionStorage.removeItem(TOKEN_KEY);
    window.sessionStorage.removeItem(REFRESH_KEY);
  }
}

/** Exchange the stored refresh token for a new pair; throws on failure. */
export async function refreshSession(): Promise<void> {
  const raw = getRefreshToken();
  if (!raw) throw new Error("no refresh token");
  const response = await fetch("/api/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: raw }),
  });
  if (!response.ok) {
    setTokens(null);
    throw new Error("refresh failed");
  }
  setTokens((await response.json()) as { access_token: string; refresh_token: string });
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly body: unknown,
  ) {
    super(`HTTP ${status}`);
    this.name = "ApiError";
  }
}

export interface RequestOptions {
  method?: string;
  body?: unknown;
  form?: URLSearchParams;
  /** Pass `null` to send the request without a token. */
  token?: string | null;
}

export interface RawResponse {
  status: number;
  body: unknown;
}

export async function rawRequest(
  path: string,
  options: RequestOptions = {},
): Promise<RawResponse> {
  const { method = "GET", body, form } = options;
  const token = options.token === undefined ? getToken() : options.token;

  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload: BodyInit | undefined;
  if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = form.toString();
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const response = await fetch(path, { method, headers, body: payload });
  const text = await response.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }
  return { status: response.status, body: parsed };
}

interface InternalOptions extends RequestOptions {
  /** Set on the single automatic retry after a refresh, to stop looping. */
  _retried?: boolean;
}

export async function request<T>(
  path: string,
  options: InternalOptions = {},
): Promise<T> {
  const { status, body } = await rawRequest(path, options);
  if (status >= 200 && status < 300) return body as T;
  if (status === 401 && !options._retried && options.token === undefined && getToken()) {
    // Access token expired mid-session: rotate once and retry.
    try {
      await refreshSession();
      return await request<T>(path, { ...options, _retried: true });
    } catch {
      /* fall through to the original 401 */
    }
  }
  throw new ApiError(status, body);
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const body = error.body as { detail?: unknown } | null;
    const detail = body?.detail;
    if (typeof detail === "string") return `${error.status} — ${detail}`;
    if (Array.isArray(detail)) return `${error.status} — ${JSON.stringify(detail)}`;
    return `${error.status} — ${JSON.stringify(error.body)}`;
  }
  return error instanceof Error ? error.message : String(error);
}

export interface JwtClaims {
  sub?: string;
  role?: string;
  iat?: number;
  exp?: number;
}

export function decodeToken(token: string | null): JwtClaims | null {
  if (!token) return null;
  const part = token.split(".")[1];
  if (!part) return null;
  try {
    const normalised = part.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(normalised)) as JwtClaims;
  } catch {
    return null;
  }
}
