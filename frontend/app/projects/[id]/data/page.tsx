"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import CptChart from "@/components/CptChart";

export default function DataIngestionPage({ params }: { params: { id: string } }) {
  const projectId = params.id;
  const [locations, setLocations] = useState<any[]>([]);
  const [cpts, setCpts] = useState<any[]>([]);
  const [selectedCpt, setSelectedCpt] = useState<string | null>(null);
  const [readings, setReadings] = useState<any[]>([]);

  useEffect(() => {
    api.listLocations(projectId).then(async (locs) => {
      setLocations(locs);
      const cptLocs = locs.filter((l: any) => l.location_type === "CPT");
      const allCpts = (await Promise.all(cptLocs.map((l: any) => api.listCpts(l.id)))).flat();
      setCpts(allCpts);
    });
  }, [projectId]);

  useEffect(() => {
    if (selectedCpt) api.getCptReadings(selectedCpt).then(setReadings);
  }, [selectedCpt]);

  return (
    <div>
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Investigation Locations</h3>
        {locations.length === 0 && <p className="muted">No investigation locations recorded yet.</p>}
        {locations.length > 0 && (
          <table>
            <thead><tr><th>Label</th><th>Type</th><th>Latitude</th><th>Longitude</th></tr></thead>
            <tbody>
              {locations.map((l) => (
                <tr key={l.id}>
                  <td>{l.location_label || l.id}</td>
                  <td>{l.location_type}</td>
                  <td>{l.latitude}</td>
                  <td>{l.longitude}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
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
        <h3 style={{ marginTop: 0 }}>Laboratory results, groundwater, geophysics</h3>
        <p className="muted">Import and review screens for these datasets aren't built into this workspace yet — they're on the MVP roadmap alongside real object storage for uploaded files.</p>
      </div>
    </div>
  );
}
