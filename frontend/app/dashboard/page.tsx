"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<any[] | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listProjects().then(setProjects).catch((err) => {
      if (err instanceof ApiError && err.status === 401) router.push("/login");
    });
  }, [router]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      // organization_id is intentionally omitted -- the backend defaults it
      // to the logged-in user's own organization (routers/projects.py).
      const p = await api.createProject({ name });
      setProjects((prev) => (prev ? [...prev, p] : [p]));
      setName("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create project.");
    }
  }

  return (
    <div>
      <h2>Projects</h2>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>New project</h3>
        <form onSubmit={handleCreate}>
          <div className="field">
            <label>Project name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          {error && <div className="error-text">{error}</div>}
          <button type="submit">Create project</button>
        </form>
      </div>

      <div className="card">
        {projects === null && <p className="muted">Loading...</p>}
        {projects && projects.length === 0 && <p className="muted">No projects yet.</p>}
        {projects && projects.length > 0 && (
          <table>
            <thead><tr><th>Name</th><th>Code</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td>{p.project_code || "—"}</td>
                  <td>{p.status}</td>
                  <td><Link href={`/projects/${p.id}`}>Open</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
