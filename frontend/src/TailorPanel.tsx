import { useState } from "react";
import type { DocumentOut, Profile } from "./types";

export default function TailorPanel({ matchId, profile, onClose }: { matchId: string; profile: Profile | null; onClose: () => void }) {
  const [doc, setDoc] = useState<DocumentOut | null>(null);
  const [accepted, setAccepted] = useState<Set<string>>(new Set());
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const originalById = new Map((profile?.bullets ?? []).map((b) => [b.id, b.text]));

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/matches/${matchId}/documents/resume`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const data: DocumentOut = await res.json();
      setDoc(data);
      setAccepted(new Set(data.content.sections.flatMap((s) => s.bullets.map((b) => b.id))));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function regenerate() {
    if (!doc) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/documents/${doc.id}/regenerate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data: DocumentOut = await res.json();
      setDoc(data);
      setAccepted(new Set(data.content.sections.flatMap((s) => s.bullets.map((b) => b.id))));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!doc) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/documents/${doc.id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accepted_bullet_ids: [...accepted] }),
      });
      if (!res.ok) throw new Error(await res.text());
      setDoc(await res.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function toggle(bulletId: string) {
    setAccepted((prev) => {
      const next = new Set(prev);
      next.has(bulletId) ? next.delete(bulletId) : next.add(bulletId);
      return next;
    });
  }

  const unsupportedClaims = doc?.verify_report?.claims.filter((c) => !c.supported) ?? [];

  return (
    <div className="tailor-panel">
      <div className="tailor-header">
        <h3>Tailor resume {doc && `(v${doc.version}${doc.status === "approved" ? ", approved" : ""})`}</h3>
        <button onClick={onClose}>Close</button>
      </div>

      {!doc && (
        <button disabled={busy} onClick={generate}>
          Generate tailored resume
        </button>
      )}

      {error && <p className="error">{error}</p>}

      {doc && (
        <>
          <p className="summary">{doc.content.summary}</p>

          {doc.rejected_bullets.length > 0 && (
            <div className="rejected-box">
              <strong>Rejected by the anti-fabrication check (no valid source):</strong>
              {doc.rejected_bullets.map((r, i) => (
                <div key={i}>
                  "{r.text}" — {r.reason}
                </div>
              ))}
            </div>
          )}

          {unsupportedClaims.length > 0 && (
            <div className="unsupported-box">
              <strong>Unsupported claims flagged by the verifier — review before approving:</strong>
              {unsupportedClaims.map((c, i) => (
                <div key={i}>
                  "{c.claim}" — {c.reasoning}
                </div>
              ))}
            </div>
          )}

          {doc.content.sections.map((section) => (
            <div key={section.experience_id} className="diff-section">
              <h4>{section.experience_id}</h4>
              {section.bullets.map((b) => (
                <div key={b.id} className="diff-row">
                  <input type="checkbox" checked={accepted.has(b.id)} onChange={() => toggle(b.id)} disabled={doc.status === "approved"} />
                  <div>
                    <div className="diff-original">original: {originalById.get(b.source_bullet_id) ?? "(source not loaded)"}</div>
                    <div className="diff-tailored">tailored: {b.text}</div>
                  </div>
                </div>
              ))}
            </div>
          ))}

          <div className="skills-row">Skills: {doc.content.skills.map((s) => s.canonical).join(", ")}</div>

          {doc.status !== "approved" && (
            <div className="tailor-actions">
              <input placeholder="feedback for regenerate (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} />
              <button disabled={busy} onClick={regenerate}>
                Regenerate with feedback
              </button>
              <button disabled={busy} onClick={approve}>
                Approve selected bullets ({accepted.size})
              </button>
            </div>
          )}

          {doc.status === "approved" && (
            <div className="export-row">
              <a href={`/api/documents/${doc.id}/export?format=pdf`} target="_blank" rel="noreferrer">
                Export PDF
              </a>
              <a href={`/api/documents/${doc.id}/export?format=docx`} target="_blank" rel="noreferrer">
                Export DOCX
              </a>
            </div>
          )}
        </>
      )}
    </div>
  );
}
