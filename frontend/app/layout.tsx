import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ground Intelligence",
  description: "PIGL Ground Intelligence — subsurface and engineering intelligence platform (MVP)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <header className="app-header">
            <div className="brand">Ground Intelligence</div>
            <div className="brand-sub">PIGL — MVP</div>
            <nav style={{ marginLeft: "auto", display: "flex", gap: 16 }}>
              <Link href="/dashboard" style={{ color: "white", opacity: 0.85, textDecoration: "none", fontSize: "0.9rem" }}>Projects</Link>
              <Link href="/admin" style={{ color: "white", opacity: 0.85, textDecoration: "none", fontSize: "0.9rem" }}>Admin</Link>
            </nav>
          </header>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
