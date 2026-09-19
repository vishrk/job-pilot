import { useEffect, useState } from "react";
import type { Company, MatchResult } from "./types";
import "./App.css";

export default function App() {
  const [email, setEmail] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [profileId, setProfileId] = useState<string | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [inbox, setInbox] = useState<MatchResult[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/companies")
      .then((r) => r.json())
      .then(setCompanies)
      .catch(() => setError("Could not load companies"));
  }, []);

  async function uploadResume() {
    if (!file || !email) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("email", email);
      const res = await fetch("/api/profile", { method: "POST", body: form });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setProfileId(data.profile_id);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function findMatches() {
    if (!profileId || selected.size === 0) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/matches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: profileId, company_ids: [...selected] }),
      });
      if (!res.ok) throw new Error(await res.text());
      setMatches(await res.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function saveAsHunt() {
    if (!email || selected.size === 0) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/hunts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, company_ids: [...selected], schedule: "daily" }),
      });
      if (!res.ok) throw new Error(await res.text());
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function loadInbox() {
    if (!email) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/matches/inbox?email=${encodeURIComponent(email)}`);
      if (!res.ok) throw new Error(await res.text());
      setInbox(await res.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function dismiss(matchId: string) {
    await fetch(`/api/matches/${matchId}/dismiss`, { method: "POST" });
    setInbox((prev) => prev.filter((m) => m.match_id !== matchId));
  }

  function toggleCompany(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleExpanded(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  return (
    <div className="page">
      <h1>JobPilot</h1>

      <section>
        <h2>1. Upload resume</h2>
        <input type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input type="file" accept=".pdf,.docx" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <button disabled={!file || !email || busy} onClick={uploadResume}>
          Upload
        </button>
        {profileId && <span className="ok"> Profile ready ({profileId.slice(0, 8)})</span>}
      </section>

      <section>
        <h2>2. Pick companies</h2>
        <div className="company-grid">
          {companies.map((c) => (
            <label key={c.id}>
              <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggleCompany(c.id)} />
              {c.name}
            </label>
          ))}
        </div>
        <button disabled={!profileId || selected.size === 0 || busy} onClick={findMatches}>
          Find matches
        </button>
        <button disabled={!profileId || selected.size === 0 || busy} onClick={saveAsHunt}>
          Save as Hunt (runs daily)
        </button>
      </section>

      {error && <p className="error">{error}</p>}
      {busy && <p>Working…</p>}

      <section>
        <h2>3. Ranked matches</h2>
        {matches.map((m) => (
          <div key={m.match_id ?? m.job_id} className="match">
            <div className="match-header" onClick={() => toggleExpanded(m.match_id)}>
              <strong>{m.title}</strong> @ {m.company} — {m.location ?? "n/a"}
              <span className="score">
                {m.score === null ? `EXCLUDED (${m.gates.status})` : `${m.score}/100`}
              </span>
            </div>
            {expanded.has(m.match_id) && (
              <div className="breakdown">
                {m.gates.checks.map((c) => (
                  <div key={c.gate} className={c.passed ? "gate-pass" : "gate-fail"}>
                    {c.gate}: {c.passed ? "pass" : c.reason}
                  </div>
                ))}
                {Object.entries(m.components).map(([k, v]) => (
                  <div key={k}>
                    {k}: {v.toFixed(2)}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </section>

      <section>
        <h2>4. Hunt inbox</h2>
        <button disabled={!email || busy} onClick={loadInbox}>
          Refresh inbox
        </button>
        {inbox.map((m) => (
          <div key={m.match_id} className="match">
            <div className="match-header">
              {m.is_new && <span className="badge">NEW</span>} <strong>{m.title}</strong> @ {m.company} —{" "}
              {m.location ?? "n/a"}
              <span className="score">{m.score === null ? "EXCLUDED" : `${m.score}/100`}</span>
              <button onClick={() => dismiss(m.match_id)}>Dismiss</button>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
