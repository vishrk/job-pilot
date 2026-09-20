import type { ExtensionProfile, FormField, FormMapResult } from "./types.ts";

// The API origin. In production this would be the real HTTPS API domain; the
// profile vault is fetched over TLS into this in-memory variable only — never
// written to chrome.storage (§7 Phase 3, §6 security). It lives only as long as
// this service worker instance does, which Chrome may recycle at any time —
// that's a feature here, not a bug: a recycled worker means the vault is gone
// until the user re-authenticates, not silently persisted.
const API_BASE = "http://localhost:8000";

let session: { email: string; profile: ExtensionProfile } | null = null;

type Message =
  | { type: "login"; email: string }
  | { type: "logout" }
  | { type: "getSession" }
  | { type: "resolveForm"; domain: string; formFingerprint: string; fields: FormField[] }
  | { type: "resolveAnswer"; question: string };

chrome.runtime.onMessage.addListener((message: Message, _sender, sendResponse) => {
  handle(message).then(sendResponse);
  return true; // keep the message channel open for the async response
});

async function handle(message: Message): Promise<unknown> {
  switch (message.type) {
    case "login": {
      const res = await fetch(`${API_BASE}/profile/vault?email=${encodeURIComponent(message.email)}`);
      if (!res.ok) return { ok: false, error: await res.text() };
      const data = await res.json();
      session = { email: message.email, profile: data.profile };
      return { ok: true, profile: session.profile };
    }
    case "logout":
      session = null;
      return { ok: true };
    case "getSession":
      return { ok: true, session };
    case "resolveForm": {
      const res = await fetch(`${API_BASE}/form-maps/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: message.domain, form_fingerprint: message.formFingerprint, fields: message.fields }),
      });
      if (!res.ok) return { ok: false, error: await res.text() };
      const result: FormMapResult = await res.json();
      return { ok: true, result };
    }
    case "resolveAnswer": {
      if (!session) return { ok: false, error: "not logged in" };
      const res = await fetch(`${API_BASE}/answers/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: session.email, question: message.question }),
      });
      if (!res.ok) return { ok: false, error: await res.text() };
      return { ok: true, ...(await res.json()) };
    }
  }
}
