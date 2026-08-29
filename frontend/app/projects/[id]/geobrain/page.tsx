"use client";

export default function GeoBrainPage() {
  return (
    <div>
      <div className="notice">
        <b>Not wired up yet.</b> GeoBrain's tool contract and the underlying data-backed functions exist in
        the backend, but the conversational (LLM) layer isn't connected in this build — this screen is a
        preview of the intended interface, not a working chat. Nothing below is live.
      </div>

      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 18, padding: "26px 28px" }}>
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <div style={{ maxWidth: "74%", padding: "12px 16px", borderRadius: 14, borderBottomRightRadius: 4, background: "var(--gi-text)", color: "var(--gi-bg)", fontSize: 13.5 }}>
            What's the design bearing resistance we ended up with for the square pad case, and which method backs it up?
          </div>
        </div>
        <div style={{ display: "flex" }}>
          <div style={{ maxWidth: "74%", padding: "12px 16px", borderRadius: 14, borderBottomLeftRadius: 4, background: "var(--gi-bg)", border: "1px solid var(--gi-border)", fontSize: 13.5, lineHeight: 1.6 }}>
            For this project's approved square-pad case, the design R/A is <b>128.511715 kN/m²</b>, from the
            Eurocode 7 DA1-Combination 2, Annex D formulation — your organization's approved v1.0 methodology.
            <div style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "var(--gi-teal-bg)", color: "var(--gi-teal)", fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 100, marginTop: 10 }}>
              run_engineering_calculation
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ display: "flex", gap: 10 }}>
        <input placeholder="Ask GeoBrain about this project… (not yet connected)" disabled />
        <button disabled style={{ flexShrink: 0 }}>Send</button>
      </div>
    </div>
  );
}
