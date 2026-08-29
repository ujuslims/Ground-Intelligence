"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";

const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

export default function OverviewPage({ params }: { params: { id: string } }) {
  const projectId = params.id;
  const [locations, setLocations] = useState<any[]>([]);
  const [calcs, setCalcs] = useState<any[] | null>(null);

  useEffect(() => {
    api.listLocations(projectId).then(setLocations);
    api.listCalculations(projectId).then(setCalcs).catch(() => setCalcs([]));
  }, [projectId]);

  const cptCount = locations.filter((l) => l.location_type === "CPT").length;
  const boreholeCount = locations.filter((l) => l.location_type === "BOREHOLE").length;
  const approvedCount = (calcs || []).filter((c) => c.latest_outcome === "COMPLETED").length;

  return (
    <div>
      <div className="gi-stats">
        <div className="gi-stat"><div className="gi-stat-label">Locations</div><div className="gi-stat-value">{locations.length}</div></div>
        <div className="gi-stat"><div className="gi-stat-label">CPTs</div><div className="gi-stat-value">{cptCount}</div></div>
        <div className="gi-stat"><div className="gi-stat-label">Boreholes</div><div className="gi-stat-value">{boreholeCount}</div></div>
        <div className="gi-stat"><div className="gi-stat-label">Completed calculations</div><div className="gi-stat-value">{calcs === null ? "—" : approvedCount}</div></div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Investigation Location Map</h3>
        <MapView locations={locations} />
      </div>
    </div>
  );
}
