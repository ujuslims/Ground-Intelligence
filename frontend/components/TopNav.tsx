"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";

/**
 * Simple top bar for pages outside a project workspace (login, the project
 * list, admin). Once inside a project (/projects/[id]/...), AppShell's own
 * sidebar carries the brand and nav instead, so this renders nothing there
 * to avoid double branding.
 *
 * The subtitle next to "Ground Intelligence" is the logged-in user's own
 * organization name, fetched from /api/auth/me -- Ground Intelligence is a
 * multi-tenant platform, so this must never be a hardcoded firm name.
 */
export default function TopNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [orgName, setOrgName] = useState<string | null>(null);

  useEffect(() => {
    api.me().then((me: any) => setOrgName(me.organization_name || null)).catch(() => {});
  }, []);

  if (pathname?.startsWith("/projects/")) return null;

  async function handleLogout() {
    try {
      await api.logout();
    } finally {
      router.push("/login");
    }
  }

  return (
    <header className="app-header" style={{
      background: "var(--gi-text)", color: "var(--gi-bg)",
      padding: "14px 24px", display: "flex", alignItems: "baseline", gap: 10,
    }}>
      <div style={{ fontWeight: 700, fontSize: "1.05rem" }} className="display">Ground Intelligence</div>
      {orgName && <div style={{ opacity: 0.7, fontSize: "0.85rem" }}>{orgName}</div>}
      <nav style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 16 }}>
        <Link href="/dashboard" style={{ color: "var(--gi-bg)", opacity: 0.85, textDecoration: "none", fontSize: "0.9rem" }}>Projects</Link>
        <Link href="/admin" style={{ color: "var(--gi-bg)", opacity: 0.85, textDecoration: "none", fontSize: "0.9rem" }}>Admin</Link>
        <button
          type="button"
          onClick={handleLogout}
          style={{
            background: "transparent", border: "1px solid rgba(255,255,255,0.35)", color: "var(--gi-bg)",
            opacity: 0.9, fontSize: "0.85rem", padding: "5px 12px", borderRadius: 100, cursor: "pointer",
          }}
        >
          Log out
        </button>
      </nav>
    </header>
  );
}
