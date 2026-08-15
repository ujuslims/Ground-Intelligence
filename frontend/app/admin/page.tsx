"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";

/**
 * Minimal, data-driven Admin/RBAC screen (Implementation Design Rev 2
 * Amendment 4) -- not an enterprise administration subsystem. Backed
 * directly by GET /api/admin/roles and POST /api/admin/users, which are
 * themselves gated by the "admin:manage_users" permission (only the
 * ADMINISTRATOR role holds it by default -- see backend/scripts/seed_rbac.py).
 */
export default function AdminPage() {
  const [roles, setRoles] = useState<any[] | null>(null);
  const [form, setForm] = useState({ email: "", full_name: "", password: "", role_name: "", project_id: "" });
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listRoles().then(setRoles).catch((err) => {
      if (err instanceof ApiError && err.status === 403) {
        setError("You don't hold the admin:manage_users permission on any project -- ask an Administrator to grant it.");
      } else if (err instanceof ApiError && err.status === 401) {
        setError("Please log in first.");
      }
    });
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    try {
      const created = await api.createUser(form as any);
      setResult(`Created ${created.email} with role ${created.role}.`);
      setForm({ email: "", full_name: "", password: "", role_name: "", project_id: form.project_id });
    } catch (err) {
      setError("Could not create user. Check the fields and that the project ID is valid.");
    }
  }

  return (
    <div>
      <h2>Admin — Users &amp; Roles</h2>
      <p className="muted">
        Six MVP roles: ENGINEER, TECHNICAL_REVIEWER, LABORATORY_USER, PROJECT_MANAGER, ADMINISTRATOR,
        CLIENT_EXTERNAL_REVIEWER. Permissions are data (RolePermission rows), not hard-coded — adjust the
        matrix in <code>backend/scripts/seed_rbac.py</code> and re-seed rather than editing application code.
      </p>

      {error && <div className="card gate-notice">{error}</div>}

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Roles</h3>
        {roles === null && !error && <p className="muted">Loading...</p>}
        {roles && (
          <table>
            <thead><tr><th>Role</th><th>Description</th></tr></thead>
            <tbody>
              {roles.map((r) => <tr key={r.id}><td>{r.name}</td><td className="muted">{r.description}</td></tr>)}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Add a user to a project</h3>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Project ID</label>
            <input value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })} required />
          </div>
          <div className="field">
            <label>Full name</label>
            <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
          </div>
          <div className="field">
            <label>Email</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </div>
          <div className="field">
            <label>Temporary password</label>
            <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          </div>
          <div className="field">
            <label>Role</label>
            <select value={form.role_name} onChange={(e) => setForm({ ...form, role_name: e.target.value })} required>
              <option value="">Select a role...</option>
              {(roles || []).map((r) => <option key={r.id} value={r.name}>{r.name}</option>)}
            </select>
          </div>
          <button type="submit">Create user</button>
        </form>
        {result && <p style={{ color: "#1a7a34", marginTop: 12 }}>{result}</p>}
      </div>
    </div>
  );
}
