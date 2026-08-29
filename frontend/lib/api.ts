/**
 * Thin fetch wrapper for the Ground Intelligence API.
 *
 * Auth is server-managed session cookies (Rev 2 §I.1) -- credentials:
 * "include" on every call, no token handling here, nothing touches
 * localStorage.
 *
 * API_BASE is deliberately empty: every call below hits a RELATIVE /api/...
 * path on this frontend's own origin, which next.config.js rewrites
 * server-side to the real backend (see the comment there). The browser never
 * makes a cross-origin request, so the backend's session cookie behaves like
 * an ordinary same-site cookie even though frontend and backend are two
 * separate deployed services.
 */
const API_BASE = "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<{ id: string; email: string; full_name: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  me: () => request<{ id: string; email: string; full_name: string }>("/api/auth/me"),

  listProjects: () => request<any[]>("/api/projects"),
  createProject: (payload: { organization_id: string; name: string; project_code?: string; description?: string }) =>
    request<any>("/api/projects", { method: "POST", body: JSON.stringify(payload) }),
  getProject: (id: string) => request<any>(`/api/projects/${id}`),

  listLocations: (projectId: string) => request<any[]>(`/api/projects/${projectId}/locations`),
  listInvestigations: (projectId: string) => request<any[]>(`/api/projects/${projectId}/investigations`),

  listCpts: (locationId: string) => request<any[]>(`/api/locations/${locationId}/cpts`),
  getCptReadings: (cptId: string) => request<any[]>(`/api/cpts/${cptId}/readings`),

  getMethodologies: (calculationType: string) =>
    request<any[]>(`/api/methodologies?calculation_type=${encodeURIComponent(calculationType)}`),

  getMethodologyVersions: (methodologyId: string) =>
    request<any[]>(`/api/methodologies/${methodologyId}/versions`),

  createCalculation: (payload: {
    project_id: string;
    calculation_type: string;
    methodology_id?: string;
    methodology_version_id?: string;
  }) => request<any>("/api/calculations", { method: "POST", body: JSON.stringify(payload) }),

  runCalculation: (calculationId: string, inputs: Record<string, any>) =>
    request<any>(`/api/calculations/${calculationId}/run`, { method: "POST", body: JSON.stringify({ inputs }) }),

  listCalculations: (projectId: string) => request<any[]>(`/api/projects/${projectId}/calculations`),

  generateDraftSummary: (projectId: string) =>
    request<any>(`/api/projects/${projectId}/reports/draft-summary`, { method: "POST" }),

  auditEvents: (projectId: string) => request<any[]>(`/api/projects/${projectId}/audit-events`),

  listRoles: () => request<any[]>("/api/admin/roles"),
  createUser: (payload: { email: string; full_name: string; password: string; role_name: string; project_id: string }) =>
    request<any>("/api/admin/users", { method: "POST", body: JSON.stringify(payload) }),
};
