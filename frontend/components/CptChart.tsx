"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

type Reading = { depth: number; qc: number | null; fs: number | null; u2: number | null };

/** qc vs depth / fs vs depth visualization (Tech Spec §18). Depth increases
 * downward on the y-axis, matching standard CPT presentation convention. */
export default function CptChart({ readings }: { readings: Reading[] }) {
  const data = [...readings].sort((a, b) => a.depth - b.depth);

  return (
    <ResponsiveContainer width="100%" height={360}>
      <LineChart data={data} layout="vertical" margin={{ left: 10, right: 20 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" />
        <YAxis type="number" dataKey="depth" reversed domain={["dataMin", "dataMax"]} label={{ value: "Depth (m)", angle: -90, position: "insideLeft" }} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="qc" stroke="#1a73c1" dot={false} name="qc (MPa)" />
        <Line type="monotone" dataKey="fs" stroke="#c1791a" dot={false} name="fs (MPa)" />
        <Line type="monotone" dataKey="u2" stroke="#7a1ac1" dot={false} name="u2 (MPa)" />
      </LineChart>
    </ResponsiveContainer>
  );
}
