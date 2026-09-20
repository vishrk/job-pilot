import { useEffect, useState } from "react";
import type { ExtensionProfile } from "../types.ts";

export default function Popup() {
  const [email, setEmail] = useState("");
  const [profile, setProfile] = useState<ExtensionProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    chrome.runtime.sendMessage({ type: "getSession" }).then((res) => {
      if (res.ok && res.session) setProfile(res.session.profile);
    });
  }, []);

  async function login() {
    setBusy(true);
    setError(null);
    const res = await chrome.runtime.sendMessage({ type: "login", email });
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setProfile(res.profile);
  }

  async function logout() {
    await chrome.runtime.sendMessage({ type: "logout" });
    setProfile(null);
  }

  return (
    <div style={{ width: 280, padding: 12, fontFamily: "system-ui, sans-serif", fontSize: 13 }}>
      <h3 style={{ margin: "0 0 8px" }}>JobPilot</h3>
      {profile ? (
        <>
          <p>Signed in as {profile.contact.name || profile.contact.email}</p>
          <p style={{ color: "#666" }}>Open a Greenhouse or Lever application page to autofill it.</p>
          <button onClick={logout}>Sign out</button>
        </>
      ) : (
        <>
          <input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ width: "100%", marginBottom: 8 }}
          />
          <button disabled={!email || busy} onClick={login}>
            Sign in
          </button>
          {error && <p style={{ color: "#b00020" }}>{error}</p>}
        </>
      )}
    </div>
  );
}
