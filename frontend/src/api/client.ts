import type { AuthResponse } from "../types";

const defaultApiBaseUrl = `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;
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

type ApiErrorField = { field?: string; loc?: Array<string | number>; message?: string; msg?: string };

function fallbackMessage(status: number): string {
  if (status === 403) return "You do not have permission to perform this action.";
  if (status === 404) return "The requested invoice was not found.";
  if (status === 409) return "This invoice was changed by another user. Reload it before saving.";
  if (status === 422) return "Please correct the highlighted information and try again.";
  if (status >= 500) return "The server could not complete this request. Please try again.";
  return "The request could not be completed.";
}

export async function toApiError(response: Response): Promise<ApiError> {
  const raw = await response.text();
  let payload: unknown = raw;
  try { payload = raw ? JSON.parse(raw) : undefined; } catch { /* Non-JSON responses use their text below. */ }
  const body = payload && typeof payload === "object" ? payload as Record<string, unknown> : undefined;
  const detail = body?.detail;
  const detailObject = detail && typeof detail === "object" && !Array.isArray(detail) ? detail as Record<string, unknown> : undefined;
  const validation = Array.isArray(detail) ? detail as ApiErrorField[] : detailObject?.fields;
  const fields = Array.isArray(validation) ? validation.map((field: ApiErrorField) => ({ field: field.field ?? field.loc?.filter((part: string | number) => part !== "body").join(".") ?? "field", message: field.message ?? field.msg ?? "Invalid value" })) : undefined;
  const validationMessage = fields?.length ? fields.map((field) => `${field.field}: ${field.message}`).join("; ") : undefined;
  const detailMessage = typeof detail === "string" ? detail : typeof detailObject?.message === "string" ? detailObject.message : typeof body?.message === "string" ? body.message : undefined;
  const message = validationMessage ?? (response.status >= 500 ? fallbackMessage(response.status) : detailMessage ?? (typeof payload === "string" && payload.trim() ? payload.trim() : fallbackMessage(response.status)));
  const code = typeof detailObject?.code === "string" ? detailObject.code : typeof body?.code === "string" ? body.code : undefined;
  return new ApiError(message, response.status, code, fields);
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

function handleUnauthorized(status: number): void {
  if (status !== 401 || !getToken()) return;
  clearToken();
  window.dispatchEvent(new Event("rainbow:unauthorized"));
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    handleUnauthorized(response.status);
    throw await toApiError(response);
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
    handleUnauthorized(response.status);
    throw await toApiError(response);
  }
  return response.blob();
}

async function requestBlobWithBody(path: string, body: unknown): Promise<Blob> {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE_URL}${path}`, { method: "POST", headers, body: JSON.stringify(body ?? {}) });
  if (!response.ok) {
    handleUnauthorized(response.status);
    throw await toApiError(response);
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
  postBlob: (path: string, body?: unknown) => requestBlobWithBody(path, body),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body ?? {}) }),
  put: <T>(path: string, body: unknown) => request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) => request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: "DELETE" })
};
