import type { FormField } from "../types.ts";

// Same algorithm as backend/app/services/form_fingerprint.py — ordered hash of
// field type/label/name, so a form's structure (not its runtime DOM ids)
// determines its cache key.
export async function fingerprint(fields: FormField[]): Promise<string> {
  const parts = fields.map((f) => `${f.field_type}|${f.label ?? ""}|${f.name_attr ?? ""}`);
  const input = parts.join("||");
  const bytes = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
