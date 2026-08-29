"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import AppShell from "@/components/AppShell";

const TITLES: Record<string, { title: string; subtitle?: string }> = {
  "": { title: "Overview" },
  data: { title: "Data Ingestion", subtitle: "Investigation locations, CPTs, boreholes, lab results" },
  analysis: { title: "Analysis", subtitle: "Engineering calculations" },
  results: { title: "Results", subtitle: "Reviewed calculation record" },
  reports: { title: "Reports", subtitle: "Preliminary and final report generation" },
  geobrain: { title: "GeoBrain", subtitle: "AI engineering assistant — this project" },
};

function segmentFromPathname(pathname: string | null, projectId: string): string {
  if (!pathname) return "";
  const rest = pathname.replace(`/projects/${projectId}`, "").replace(/^\//, "");
  return rest.split("/")[0] || "";
}

export default function ProjectLayout({ children, params }: { children: React.ReactNode; params: { id: string } }) {
  const projectId = params.id;
  const pathname = usePathname();
  const router = useRouter();
  const [project, setProject] = useState<any>(null);
  const [me, setMe] = useState<any>(null);

  useEffect(() => {
    api.getProject(projectId).then(setProject).catch((err) => {
      if (err instanceof ApiError && err.status === 401) router.push("/login");
    });
    api.me().then(setMe).catch(() => {});
  }, [projectId, router]);

  const seg = segmentFromPathname(pathname, projectId);
  const { title, subtitle } = TITLES[seg] || TITLES[""];
  const initials = me?.full_name
    ? me.full_name.split(" ").map((p: string) => p[0]).slice(0, 2).join("").toUpperCase()
    : "?";

  return (
    <AppShell
      projectId={projectId}
      projectName={project?.name}
      projectCode={project?.project_code}
      userInitials={initials}
      title={title}
      subtitle={subtitle}
    >
      {!project ? <p className="muted">Loading...</p> : children}
    </AppShell>
  );
}
