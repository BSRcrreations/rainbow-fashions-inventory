import type { AuthResponse } from "../types";

const defaultApiBaseUrl = `${window.location.protocol}//${window.location.host}/api/v1`;
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl;
const TOKEN_KEY = "rainbow_inventory_token";

export class ApiError extends Error {
  status: number;
  code?: string;
  fields?: Array<{ field: string; message: string }>;

  constructor(message: string, status: number, code?: string, fields?: Array<{ field: string; message: string }>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    const detail = error.detail;
    if (typeof detail === "string") {
      throw new ApiError(detail, response.status);
    }
    if (detail && typeof detail === "object") {
      throw new ApiError(detail.message ?? "Request failed", response.status, detail.code, detail.fields);
    }
    throw new ApiError("Request failed", response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function requestBlob(path: string): Promise<Blob> {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE_URL}${path}`, { headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    const detail = error.detail;
    if (typeof detail === "string") throw new ApiError(detail, response.status);
    if (detail && typeof detail === "object") throw new ApiError(detail.message ?? "Request failed", response.status, detail.code, detail.fields);
    throw new ApiError("Request failed", response.status);
  }
  return response.blob();
}

export const api = {
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    }),
  me: <T>() => request<T>("/auth/me"),
  logout: () => request<{ message: string }>("/auth/logout", { method: "POST" }),
  get: <T>(path: string) => request<T>(path),
  getBlob: (path: string) => requestBlob(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body ?? {}) }),
  put: <T>(path: string, body: unknown) => request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: "DELETE" })
};
