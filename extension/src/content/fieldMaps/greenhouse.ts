import type { FormField, ProfileFieldPath } from "../../types.ts";
import { labelMatches } from "./common.ts";

// Greenhouse's embedded application form (boards.greenhouse.io/embed/job_app) uses
// consistent field names/labels across every company's board — "first_name",
// "last_name", "email", "phone", "resume", "cover_letter" — so a label/name
// pattern match is reliable without per-company selectors.
export function matchGreenhouseField(field: FormField): ProfileFieldPath | null {
  if (field.field_type === "file") {
    if (labelMatches(field, /resum|cv/)) return "resume_file";
    if (labelMatches(field, /cover.?letter/)) return "cover_letter_file";
    return null;
  }
  if (labelMatches(field, /first.?name/) || labelMatches(field, /^name$/)) return "contact.name";
  if (labelMatches(field, /last.?name/)) return "contact.name"; // combined into one name field value upstream
  if (labelMatches(field, /email/)) return "contact.email";
  if (labelMatches(field, /phone/)) return "contact.phone";
  if (labelMatches(field, /location|city/)) return "contact.location";
  if (labelMatches(field, /work.?authoriz|sponsorship|visa/)) return "work_authorization.status";
  if (labelMatches(field, /current.?(company|employer)/)) return "most_recent.company";
  if (labelMatches(field, /current.?title|job.?title/)) return "most_recent.title";
  if (labelMatches(field, /school|university|institution/)) return "education.institution";
  if (labelMatches(field, /degree/)) return "education.degree";
  return null;
}
