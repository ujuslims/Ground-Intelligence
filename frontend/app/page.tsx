import Link from "next/link";

export default function Home() {
  return (
    <div className="card">
      <h2>Welcome to Ground Intelligence</h2>
      <p className="muted">
        Multidisciplinary subsurface and engineering intelligence platform — MVP build.
      </p>
      <p>
        <Link href="/login">Log in</Link> to view your projects.
      </p>
    </div>
  );
}
