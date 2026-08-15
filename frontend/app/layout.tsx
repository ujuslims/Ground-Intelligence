import type { Metadata } from "next";
import "./globals.css";

// Uses the system font stack rather than next/font/google's Geist download
// -- avoids a build-time dependency on fonts.googleapis.com being
// reachable (irrelevant to app behavior; swap back to next/font/google
// later if a specific PIGL brand font is required).

export const metadata: Metadata = {
  title: "Ground Intelligence",
  description: "Polaris Integrated & Geosolutions Limited (PIGL) subsurface and engineering intelligence platform",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
