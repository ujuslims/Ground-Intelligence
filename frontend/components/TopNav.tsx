"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * Simple top bar for pages outside a project workspace (login, the project
 * list, admin). Once inside a project (/projects/[id]/...), AppShell's own
 * sidebar carries the brand and nav instead, so this renders nothing there
 * to avoid double branding.
 */
export default function TopNav() {
  const pathname = usePathname();
  if (pathname?.startsWith("/projects/")) return null;

  return (
    <header className="app-header" style={{
      background: "var(--gi-text)", color: "var(--gi-bg)",
      padding: "14px 24px", display: "flex", alignItems: "baseline", gap: 10,
    }}>
      <div style={{ fontWeight: 700, fontSize: "1.05rem" }} className="display">Ground Intelligence</div>
      <div style={{ opacity: 0.7, fontSize: "0.85rem" }}>PIGL — MVP</div>
      <nav style={{ marginLeft: "auto", display: "flex", gap: 16 }}>
        <Link href="/dashboard" style={{ color: "var(--gi-bg)", opacity: 0.85, textDecoration: "none", fontSize: "0.9rem" }}>Projects</Link>
        <Link href="/admin" style={{ color: "var(--gi-bg)", opacity: 0.85, textDecoration: "none", fontSize: "0.9rem" }}>Admin</Link>
      </nav>
    </header>
  );
}
