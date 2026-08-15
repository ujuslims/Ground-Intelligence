import { redirect } from "next/navigation";

export default function RootPage() {
  // Phase 1 has no marketing/landing page -- the app starts at login.
  redirect("/login");
}
