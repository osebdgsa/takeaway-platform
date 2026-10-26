const TOKEN_KEY = "takeaway.token";

// sessionStorage, not localStorage: the token does not survive a closed tab,
// so a stolen token has a smaller window. Authorisation is still enforced
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

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { status, body } = await rawRequest(path, options);
  if (status >= 200 && status < 300) return body as T;
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
