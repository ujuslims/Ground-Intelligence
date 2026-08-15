"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("demo.engineer@pigl.example");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? "Invalid email or password." : "Could not reach the API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card" style={{ maxWidth: 420, margin: "40px auto" }}>
      <h2>Log in</h2>
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="field">
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        {error && <div className="error-text">{error}</div>}
        <button type="submit" disabled={loading}>{loading ? "Signing in..." : "Sign in"}</button>
      </form>
      <p className="muted" style={{ marginTop: 16 }}>
        Demo credentials (after running <code>scripts/seed_demo_data.py</code>):<br />
        demo.engineer@pigl.example / DemoPass123!
      </p>
    </div>
  );
}
