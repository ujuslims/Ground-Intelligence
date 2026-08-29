"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { applyTheme, getStoredTheme, GiTheme } from "@/lib/theme";

const NAV_ICONS: Record<string, JSX.Element> = {
  overview: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1.3" /><rect x="14" y="3" width="7" height="7" rx="1.3" />
      <rect x="3" y="14" width="7" height="7" rx="1.3" /><rect x="14" y="14" width="7" height="7" rx="1.3" />
    </svg>
  ),
  data: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v10M8 9l4-4 4 4" /><path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
    </svg>
  ),
  analysis: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 2v6.3L4.2 19a2 2 0 0 0 1.8 2.9h12a2 2 0 0 0 1.8-2.9L15 8.3V2" /><path d="M9 2h6" /><path d="M7.5 15h9" />
    </svg>
  ),
  results: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" /><path d="M8 12.5l2.5 2.5L16 9" />
    </svg>
  ),
  reports: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /><path d="M8 13h8M8 17h8M8 9h2" />
    </svg>
  ),
  geobrain: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 5h16a1.6 1.6 0 0 1 1.6 1.6v8.4a1.6 1.6 0 0 1-1.6 1.6H10l-4.2 3.6V16.6H4A1.6 1.6 0 0 1 2.4 15V6.6A1.6 1.6 0 0 1 4 5z" />
      <path d="M15.5 4.2l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6z" />
    </svg>
  ),
};

// Order deliberately keeps the Data -> Analysis -> Results -> Reports pipeline
// unbroken; GeoBrain sits last as a standalone assistant, not a pipeline step.
const NAV_ITEMS = [
  { key: "overview", label: "Overview", href: (id: string) => `/projects/${id}` },
  { key: "data", label: "Data Ingestion", href: (id: string) => `/projects/${id}/data` },
  { key: "analysis", label: "Analysis", href: (id: string) => `/projects/${id}/analysis` },
  { key: "results", label: "Results", href: (id: string) => `/projects/${id}/results` },
  { key: "reports", label: "Reports", href: (id: string) => `/projects/${id}/reports` },
  { key: "geobrain", label: "GeoBrain", href: (id: string) => `/projects/${id}/geobrain` },
];

function ThemeSwitch() {
  const [theme, setTheme] = useState<GiTheme>("warm");
  useEffect(() => setTheme(getStoredTheme()), []);
  function pick(t: GiTheme) {
    setTheme(t);
    applyTheme(t);
  }
  return (
    <div className="gi-theme-switch">
      <button type="button" className={`gi-theme-btn ${theme === "light" ? "on" : ""}`} title="Light" onClick={() => pick("light")}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round">
          <circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      </button>
      <button type="button" className={`gi-theme-btn ${theme === "warm" ? "on" : ""}`} title="Warm" onClick={() => pick("warm")}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round">
          <path d="M12 3a6 6 0 0 0 0 12 6 6 0 0 0 6-6c0 5-4 9-9 9a9 9 0 1 1 3-17.5z" />
        </svg>
      </button>
      <button type="button" className={`gi-theme-btn ${theme === "dark" ? "on" : ""}`} title="Dark" onClick={() => pick("dark")}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
      </button>
    </div>
  );
}

export default function AppShell({
  projectId,
  projectName,
  projectCode,
  userInitials,
  title,
  subtitle,
  headerRight,
  children,
}: {
  projectId: string;
  projectName?: string;
  projectCode?: string;
  userInitials?: string;
  title: string;
  subtitle?: string;
  headerRight?: React.ReactNode;
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  function isActive(key: string, href: string) {
    if (key === "overview") return pathname === href;
    return pathname?.startsWith(href);
  }

  return (
    <div className="gi-shell">
      <aside className="gi-sidebar">
        <div className="gi-brand">
          <div className="gi-brand-mark">Ground Intelligence</div>
          <div className="gi-brand-sub">PIGL — MVP</div>
        </div>
        <nav className="gi-navlist">
          {NAV_ITEMS.map((item) => {
            const href = item.href(projectId);
            return (
              <Link key={item.key} href={href} className={`gi-navitem ${isActive(item.key, href) ? "active" : ""}`}>
                {NAV_ICONS[item.key]}
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="gi-nav-spacer" />
        <div className="gi-sidebar-foot">
          {projectName || "—"}
          {projectCode ? <><br />{projectCode}</> : null}
        </div>
      </aside>

      <div className="gi-maincol">
        <div className="gi-topbar">
          <div>
            <h1 style={{ fontSize: 26 }}>{title}</h1>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <div className="gi-topbar-right">
            {headerRight}
            <ThemeSwitch />
            <div className="gi-avatar">{userInitials || "?"}</div>
          </div>
        </div>
        <div className="gi-main">{children}</div>
      </div>
    </div>
  );
}
