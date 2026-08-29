"use client";

import { Fragment, useEffect, useState } from "react";
import { api } from "@/lib/api";

const LABELS: Record<string, string> = {
  SHALLOW_FOUNDATION_BEARING_CAPACITY: "Shallow Foundation Bearing Capacity",
};

function badgeClass(outcome: string | null) {
  if (outcome === "COMPLETED") return "badge badge-completed";
  if (outcome === "REFUSED_NO_APPROVED_METHODOLOGY") return "badge badge-refused";
  return "badge badge-draft";
}

export default function ResultsPage({ params }: { params: { id: string } }) {
  const projectId = params.id;
  const [calcs, setCalcs] = useState<any[] | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    api.listCalculations(projectId).then(setCalcs);
  }, [projectId]);

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Calculation Record</h3>
      <p className="muted" style={{ marginBottom: 12 }}>
        Every calculation run on this project, with its outcome and review status — the reviewed record,
        separate from the Analysis workbench that produces it.
      </p>

      {calcs === null && <p className="muted">Loading...</p>}
      {calcs && calcs.length === 0 && <p className="muted">No calculations run on this project yet — try Analysis.</p>}
      {calcs && calcs.length > 0 && (
        <table>
          <thead><tr><th>Type</th><th>Status</th><th>Outcome</th><th>Run at</th><th></th></tr></thead>
          <tbody>
            {calcs.map((c) => (
              <Fragment key={c.id}>
                <tr>
                  <td>{LABELS[c.calculation_type] || c.calculation_type}</td>
                  <td>{c.status}</td>
                  <td><span className={badgeClass(c.latest_outcome)}>{c.latest_outcome || "—"}</span></td>
                  <td className="muted">{c.latest_created_at ? new Date(c.latest_created_at).toLocaleString() : "—"}</td>
                  <td>
                    {c.latest_result && (
                      <a href="#" onClick={(e) => { e.preventDefault(); setOpenId(openId === c.id ? null : c.id); }}>
                        {openId === c.id ? "Hide" : "View"}
                      </a>
                    )}
                  </td>
                </tr>
                {openId === c.id && c.latest_result && (
                  <tr>
                    <td colSpan={5}>
                      <table style={{ margin: "8px 0 4px" }}>
                        <tbody>
                          {Object.entries(c.latest_result)
                            .filter(([k]) => typeof (c.latest_result as any)[k] !== "object")
                            .map(([k, v]: [string, any]) => (
                              <tr key={k}><td>{k}</td><td>{String(v)}</td></tr>
                            ))}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
