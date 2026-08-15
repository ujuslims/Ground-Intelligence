"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, Project, User } from "@/lib/api";

export default function ProjectListPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const me = await api.me();
        setUser(me);
        const list = await api.listProjects();
        setProjects(list);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          router.push("/login");
          return;
        }
        setError(err instanceof ApiError ? err.message : "Failed to load projects");
      }
    }
    load();
  }, [router]);

  async function handleLogout() {
    await api.logout();
    router.push("/login");
  }

  return (
    <main className="mx-auto max-w-3xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Projects</h1>
          {user && <p className="text-sm text-slate-500">Signed in as {user.name} ({user.email})</p>}
        </div>
        {user && (
          <button
            onClick={handleLogout}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700"
          >
            Sign out
          </button>
        )}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {projects === null && !error && <p className="text-sm text-slate-500">Loading...</p>}

      {projects !== null && projects.length === 0 && (
        <p className="text-sm text-slate-500">
          No projects yet. Projects you have membership on will appear here.
        </p>
      )}

      {projects !== null && projects.length > 0 && (
        <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
          {projects.map((p) => (
            <li key={p.id} className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-900">{p.name}</p>
                  <p className="text-sm text-slate-500">{p.project_code}</p>
                </div>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{p.status}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
