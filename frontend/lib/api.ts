/**
 * Thin fetch wrapper for the Ground Intelligence backend API.
 *
 * credentials: "include" is required because auth is a server-managed
 * session cookie (Implementation Design Rev 2 §I.1) -- there is no bearer
 * token for this client to hold or store. NEXT_PUBLIC_API_URL points at
 * the FastAPI service; it is the ONLY backend this frontend talks to.
 * There is no direct Supabase client anywhere in this app -- Supabase is
 * infrastructure behind the FastAPI service, not something the frontend
 * connects to (see docs/INFRASTRUCTURE_DECISIONS.md).
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response had no JSON body; fall back to statusText
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export interface User {
  id: string;
  email: string;
  name: string;
  status: string;
}

export interface Project {
  id: string;
  project_code: string;
  name: string;
  client_id: string;
  project_type: string | null;
  description: string | null;
  location: string | null;
  status: string;
}

export const api = {
  login: (email: string, password: string) =>
    request<User>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<{ status: string }>("/auth/logout", { method: "POST" }),
  me: () => request<User>("/auth/me"),
  listProjects: () => request<Project[]>("/projects"),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
};
