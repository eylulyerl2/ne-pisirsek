import { NETWORK_ERROR, formatApiError } from "../utils/errors";

export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "nepisirsek.token";

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* özel pencerede depolama kapalı olabilir */
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* yok say */
    }
  },
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

let unauthorizedHandler: (() => void) | null = null;
export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  form?: Record<string, string>;
  params?: Record<string, string | number | boolean | string[] | undefined | null>;
  auth?: boolean;
}

function buildUrl(path: string, params: RequestOptions["params"]): string {
  const url = new URL(path, API_URL);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value === undefined || value === null || value === "") continue;
    for (const item of Array.isArray(value) ? value : [value]) url.searchParams.append(key, String(item));
  }
  return url.toString();
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, form, params, auth = true } = options;
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let payload: BodyInit | undefined;
  if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form);
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), { method, headers, body: payload });
  } catch {
    throw new ApiError(0, NETWORK_ERROR);
  }

  if (response.status === 204) return undefined as T;

  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    /* gövde yok veya JSON değil */
  }

  if (!response.ok) {
    if (response.status === 401 && auth && token) unauthorizedHandler?.();
    throw new ApiError(response.status, formatApiError(response.status, data));
  }
  return data as T;
}
