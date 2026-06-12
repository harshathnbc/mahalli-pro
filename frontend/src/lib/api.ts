/**
 * Lightweight API client for the Django backend.
 *
 * Holds the JWT access/refresh pair in localStorage and attaches the access token
 * to every request. On a 401 it transparently refreshes once and retries.
 */
const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

const ACCESS_KEY = "mp_access";
const REFRESH_KEY = "mp_refresh";

export const tokenStore = {
  get access() {
    return typeof window === "undefined" ? null : localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return typeof window === "undefined" ? null : localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function refreshAccess(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  const res = await fetch(`${BASE_URL}/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) return false;
  const data = await res.json();
  tokenStore.set(data.access);
  return true;
}

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (tokenStore.access) headers.set("Authorization", `Bearer ${tokenStore.access}`);

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401 && retry && (await refreshAccess())) {
    return apiFetch<T>(path, options, false);
  }
  if (!res.ok) {
    const detail = await res.text();
    throw new ApiError(res.status, detail || res.statusText);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export async function login(email: string, password: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/auth/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // SimpleJWT expects the USERNAME_FIELD; our users authenticate by username=email.
    body: JSON.stringify({ username: email, password }),
  });
  if (!res.ok) throw new ApiError(res.status, "Invalid credentials");
  const data = await res.json();
  tokenStore.set(data.access, data.refresh);
}

export function logout() {
  tokenStore.clear();
}
