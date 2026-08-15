"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import CptChart from "@/components/CptChart";

const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  const projectId = params.id;
  const [project, setProject] = useState<any>(null);
  const [locations, setLocations] = useState<any[]>([]);
  const [cpts, setCpts] = useState<any[]>([]);
  const [selectedCpt, setSelectedCpt] = useState<string | null>(null);
  const [readings, setReadings] = useState<any[]>([]);
  const [calcResult, setCalcResult] = useState<any>(null);
  const [calcLoading, setCalcLoading] = useState(false);
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    api.getProject(projectId).then(setProject);
    api.listLocations(projectId).then(async (locs) => {
      setLocations(locs);
      const cptLocs = locs.filter((l) => l.location_type === "CPT");
      const allCpts = (await Promise.all(cptLocs.map((l) => api.listCpts(l.id)))).flat();
      setCpts(allCpts);
    });
  }, [projectId]);

  useEffect(() => {
    if (selectedCpt) api.getCptReadings(selectedCpt).then(setReadings);
  }, [selectedCpt]);

  async function tryShallowFoundationCalculation() {
    setCalcLoading(true);
    try {
      // Demonstrates the governance gate: no APPROVED methodology exists for
      // this calculation_type, so the Runner refuses -- by design, not by bug.
      const methodologies = await api.getMethodologies("SHALLOW_FOUNDATION_BEARING_CAPACITY");
      if (methodologies.length === 0) {
        setCalcResult({
          outcome: "REFUSED_NO_APPROVED_METHODOLOGY",
          message:
            "No approved engineering methodology is available for Shallow Foundation Bearing Capacity. " +
            "Ground Intelligence does not estimate or substitute a methodology. Submit a Request/Add " +
            "Methodology to begin the PIGL Engineering review process.",
        });
      }
    } finally {
      setCalcLoading(false);
    }
  }

  async function generateSummary() {
    const s = await api.generateDraftSummary(projectId);
    setSummary(s);
  }

  if (!project) return <p className="muted">Loading...</p>;

  return (
    <div>
      <h2>{project.name}</h2>
      <p className="muted">{project.project_code} — {project.status}</p>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Investigation Location Map</h3>
        <MapView locations={locations} />
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>CPT Visualization</h3>
        {cpts.length === 0 && <p className="muted">No CPT records for this project.</p>}
        {cpts.length > 0 && (
          <>
            <select value={selectedCpt || ""} onChange={(e) => setSelectedCpt(e.target.value)}>
              <option value="">Select a CPT...</option>
              {cpts.map((c) => <option key={c.id} value={c.id}>{c.cpt_id_label}</option>)}
            </select>
            {readings.length > 0 && <div style={{ marginTop: 16 }}><CptChart readings={readings} /></div>}
          </>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Engineering Calculation — Shallow Foundation Bearing Capacity</h3>
        <div className="gate-notice">
          <strong>Governance gate:</strong> the shallow-foundation bearing-capacity methodology has not
          been supplied or approved by PIGL Engineering. Ground Intelligence will not estimate,
          approximate, or fabricate a result.
        </div>
        <button onClick={tryShallowFoundationCalculation} disabled={calcLoading}>
          {calcLoading ? "Checking..." : "Attempt calculation"}
        </button>
        {calcResult && (
          <div style={{ marginTop: 12 }}>
            <span className="badge badge-refused">{calcResult.outcome}</span>
            <p style={{ marginTop: 8 }}>{calcResult.message}</p>
          </div>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Draft Engineering Summary</h3>
        <button onClick={generateSummary}>Generate draft summary</button>
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
    </div>
  );
}
