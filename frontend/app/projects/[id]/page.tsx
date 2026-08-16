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
  const [calcMethodology, setCalcMethodology] = useState<any>(null);
  const [calcVersion, setCalcVersion] = useState<any>(null);
  const [calcChecked, setCalcChecked] = useState(false);
  const [calcForm, setCalcForm] = useState({ B: "1.0", Df: "1.0", gamma_prime: "10.57", phi: "33", applied_load_kN: "" });
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

  async function checkMethodology() {
    setCalcLoading(true);
    setCalcResult(null);
    try {
      // Governance gate: only a Methodology with an APPROVED MethodologyVersion
      // is ever surfaced here. If none exists, the calculation is correctly
      // refused rather than estimated or substituted.
      const methodologies = await api.getMethodologies("SHALLOW_FOUNDATION_BEARING_CAPACITY");
      if (methodologies.length === 0) {
        setCalcMethodology(null);
        setCalcVersion(null);
        setCalcResult({
          outcome: "REFUSED_NO_APPROVED_METHODOLOGY",
          message:
            "No approved engineering methodology is available for Shallow Foundation Bearing Capacity. " +
            "Ground Intelligence does not estimate, approximate, or substitute a methodology. Submit a " +
            "Request/Add Methodology to begin the PIGL Engineering review process.",
        });
      } else {
        const m = methodologies[0];
        setCalcMethodology(m);
        const versions = await api.getMethodologyVersions(m.id);
        setCalcVersion(versions[0] || null);
      }
    } finally {
      setCalcChecked(true);
      setCalcLoading(false);
    }
  }

  async function runShallowFoundationCalculation() {
    if (!calcMethodology || !calcVersion) return;
    setCalcLoading(true);
    try {
      const calc = await api.createCalculation({
        project_id: projectId,
        calculation_type: "SHALLOW_FOUNDATION_BEARING_CAPACITY",
        methodology_id: calcMethodology.id,
        methodology_version_id: calcVersion.id,
      });
      const inputs: Record<string, any> = {
        B: parseFloat(calcForm.B),
        Df: parseFloat(calcForm.Df),
        gamma_prime: parseFloat(calcForm.gamma_prime),
        phi: parseFloat(calcForm.phi),
      };
      if (calcForm.applied_load_kN.trim() !== "") {
        inputs.applied_load_kN = parseFloat(calcForm.applied_load_kN);
      }
      const run = await api.runCalculation(calc.id, inputs);
      setCalcResult(run);
    } catch (e: any) {
      setCalcResult({ outcome: "ERROR", message: e?.message || "Calculation request failed." });
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
          <strong>Governance gate:</strong> Ground Intelligence will only run this calculation using a
          methodology that PIGL Engineering has formally approved. If none is approved, the system
          refuses rather than estimating, approximating, or fabricating a result.
        </div>

        {!calcChecked && (
          <button onClick={checkMethodology} disabled={calcLoading}>
            {calcLoading ? "Checking..." : "Check approved methodology"}
          </button>
        )}

        {calcChecked && !calcMethodology && calcResult && (
          <div style={{ marginTop: 12 }}>
            <span className="badge badge-refused">{calcResult.outcome}</span>
            <p style={{ marginTop: 8 }}>{calcResult.message}</p>
          </div>
        )}

        {calcMethodology && calcVersion && (
          <div style={{ marginTop: 12 }}>
            <p className="muted" style={{ marginBottom: 12 }}>
              Approved methodology: <strong>{calcMethodology.name}</strong> — version {calcVersion.version}.
              Scope: square pad, drained (c′=0), vertical/concentric loading only.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0,1fr))", gap: 12, maxWidth: 480 }}>
              <label>
                Footing width B (m)
                <input value={calcForm.B} onChange={(e) => setCalcForm({ ...calcForm, B: e.target.value })} />
              </label>
              <label>
                Embedment depth Df (m)
                <input value={calcForm.Df} onChange={(e) => setCalcForm({ ...calcForm, Df: e.target.value })} />
              </label>
              <label>
                Effective unit weight γ′ (kN/m³)
                <input value={calcForm.gamma_prime} onChange={(e) => setCalcForm({ ...calcForm, gamma_prime: e.target.value })} />
              </label>
              <label>
                Friction angle φ′ (°)
                <input value={calcForm.phi} onChange={(e) => setCalcForm({ ...calcForm, phi: e.target.value })} />
              </label>
              <label>
                Applied vertical load Vd (kN) — optional
                <input value={calcForm.applied_load_kN} onChange={(e) => setCalcForm({ ...calcForm, applied_load_kN: e.target.value })} />
              </label>
            </div>
            <button style={{ marginTop: 12 }} onClick={runShallowFoundationCalculation} disabled={calcLoading}>
              {calcLoading ? "Calculating..." : "Run calculation"}
            </button>
          </div>
        )}

        {calcResult && calcMethodology && (
          <div style={{ marginTop: 16 }}>
            <span className={calcResult.outcome === "COMPLETED" ? "badge badge-draft" : "badge badge-refused"}>
              {calcResult.outcome}
            </span>
            {calcResult.message && <p style={{ marginTop: 8 }}>{calcResult.message}</p>}
            {calcResult.result && (
              <table style={{ marginTop: 12 }}>
                <tbody>
                  {Object.entries(calcResult.result)
                    .filter(([k]) => typeof calcResult.result[k] !== "object")
                    .map(([k, v]: [string, any]) => (
                      <tr key={k}><td>{k}</td><td>{String(v)}</td></tr>
                    ))}
                </tbody>
              </table>
            )}
            {calcResult.warnings && calcResult.warnings.length > 0 && (
              <ul style={{ marginTop: 8 }}>
                {calcResult.warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
              </ul>
            )}
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
