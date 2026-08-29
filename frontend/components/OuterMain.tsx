"use client";

import { usePathname } from "next/navigation";

/**
 * Outside a project workspace, content is centered with page padding (the
 * original simple layout). Inside a project (/projects/[id]/...), AppShell
 * owns the full-width sidebar layout, so this steps out of the way.
 */
export default function OuterMain({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const inProject = pathname?.startsWith("/projects/");

  if (inProject) return <>{children}</>;

  return (
    <main style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
      {children}
    </main>
  );
}
