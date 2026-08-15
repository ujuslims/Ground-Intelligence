"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

type Location = {
  id: string;
  location_code: string;
  location_type: string;
  latitude: number;
  longitude: number;
};

const COLOR_BY_TYPE: Record<string, string> = {
  BOREHOLE: "#1a73c1",
  CPT: "#c1791a",
  VES: "#7a1ac1",
  GROUNDWATER_POINT: "#1ac17a",
  TRIAL_PIT: "#c11a3d",
};

/**
 * MVP project map (Tech Spec §13, §48): a single query against
 * InvestigationLocation drives the map regardless of discipline -- boreholes,
 * CPT, VES and groundwater points render from one common location model,
 * never discipline-specific mapping implementations.
 */
export default function MapView({ locations }: { locations: Location[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const center: [number, number] = locations.length
      ? [locations[0].longitude, locations[0].latitude]
      : [3.3792, 6.5244];

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "&copy; OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
      center,
      zoom: 13,
    });
    mapRef.current = map;

    map.on("load", () => {
      locations.forEach((loc) => {
        const el = document.createElement("div");
        el.style.width = "14px";
        el.style.height = "14px";
        el.style.borderRadius = "50%";
        el.style.border = "2px solid white";
        el.style.background = COLOR_BY_TYPE[loc.location_type] || "#555";
        el.title = `${loc.location_code} (${loc.location_type})`;

        new maplibregl.Marker({ element: el })
          .setLngLat([loc.longitude, loc.latitude])
          .setPopup(new maplibregl.Popup({ offset: 12 }).setText(`${loc.location_code} — ${loc.location_type}`))
          .addTo(map);
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [locations]);

  return <div ref={containerRef} style={{ width: "100%", height: 360, borderRadius: 8, overflow: "hidden" }} />;
}
