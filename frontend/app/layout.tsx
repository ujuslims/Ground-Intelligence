import type { Metadata } from "next";
import "./globals.css";
import ThemeInit from "@/components/ThemeInit";
import TopNav from "@/components/TopNav";
import OuterMain from "@/components/OuterMain";

export const metadata: Metadata = {
  title: "Ground Intelligence",
  description: "Ground Intelligence — subsurface and engineering intelligence platform (MVP)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Public+Sans:wght@400;500;600;700&display=swap" />
      </head>
      <body>
        <ThemeInit />
        <TopNav />
        <OuterMain>{children}</OuterMain>
      </body>
    </html>
  );
}
