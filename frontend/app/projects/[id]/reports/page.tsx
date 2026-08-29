"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export default function ReportsPage({ params }: { params: { id: string } }) {
  const projectId = params.id;
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function generateSummary() {
    setLoading(true);
    try {
      const s = await api.generateDraftSummary(projectId);
      setSummary(s);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Draft Engineering Summary</h3>
      <p className="muted" style={{ marginBottom: 12 }}>
        Assembled from structured project data and reviewed/approved calculations — a preliminary draft
        for engineer review, not an approved deliverable. Final report templates (PIGL and client formats)
        are on the roadmap.
      </p>
      <button onClick={generateSummary} disabled={loading}>{loading ? "Generating..." : "Generate draft summary"}</button>
      {summary && (
        <div style={{ marginTop: 12 }}>
          <span className="badge badge-draft">{summary.label}</span>
          <table style={{ marginTop: 12 }}>
            <thead><tr><th>Section</th><th>Status</th></tr></thead>
            <tbody>
              {summary.sections?.map((s: any) => (
                <tr key={s.section_type}><td>{s.heading}</td><td>—</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
