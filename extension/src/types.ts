// Mirrors backend/app/schemas/form.py — keep the two in sync by hand for now
// (no shared codegen yet; small enough surface that drift would show up fast
// as a 422 from the API).
export type ProfileFieldPath =
  | "contact.name"
  | "contact.email"
  | "contact.phone"
  | "contact.location"
  | "work_authorization.status"
  | "most_recent.title"
  | "most_recent.company"
  | "total_years_experience"
  | "education.institution"
  | "education.degree"
  | "resume_file"
  | "cover_letter_file"
  | "essay"
  | "unknown";

export interface FormField {
  selector: string;
  label: string | null;
  field_type: string;
  name_attr: string | null;
  options?: string[] | null;
}

export interface FieldMapping {
  selector: string;
  profile_field: ProfileFieldPath;
  confidence: number;
}

export interface FormMapResult {
  mappings: FieldMapping[];
}

// Subset of the master profile the extension actually needs to fill a form —
// deliberately not the full MasterProfile shape from the backend, so a change
// to profile internals (new optional field, etc) doesn't ripple into the
// extension unless it's something autofill actually uses.
export interface ExtensionProfile {
  contact: { name: string; email: string | null; phone: string | null; location: string | null };
  work_authorization: { status: string };
  experience: { title: string; company: string }[];
  education: { institution: string | null; degree: string | null }[];
  total_years_experience: number;
}

export interface FillAction {
  selector: string;
  kind: "text" | "select" | "file" | "essay";
  value: string; // for "essay", this is the drafted answer text (always shown for edit)
  source: ProfileFieldPath;
}
