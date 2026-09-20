import type { FormField, ProfileFieldPath } from "../../types.ts";
import { labelMatches } from "./common.ts";

// Lever's hosted application form (jobs.lever.co/{company}/{id}/apply) also uses
// consistent field labels across postings: "Full name", "Email", "Phone",
// "Resume/CV", "Current company", "Current title".
export function matchLeverField(field: FormField): ProfileFieldPath | null {
  if (field.field_type === "file") {
    if (labelMatches(field, /resum|cv/)) return "resume_file";
    if (labelMatches(field, /cover.?letter/)) return "cover_letter_file";
    return null;
  }
  if (labelMatches(field, /full.?name|^name$/)) return "contact.name";
  if (labelMatches(field, /email/)) return "contact.email";
  if (labelMatches(field, /phone/)) return "contact.phone";
  if (labelMatches(field, /location|current.?location/)) return "contact.location";
  if (labelMatches(field, /current.?company/)) return "most_recent.company";
  if (labelMatches(field, /current.?title/)) return "most_recent.title";
  return null;
}
