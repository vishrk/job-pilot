import type { ExtensionProfile, FieldMapping, FillAction, ProfileFieldPath } from "../types.ts";

// Below this confidence, leave the field for the user rather than risk filling
// it wrong — matches the form-mapper's own LOW_CONFIDENCE threshold server-side.
const FILL_CONFIDENCE_THRESHOLD = 0.6;

function resolveValue(field: ProfileFieldPath, profile: ExtensionProfile): string | null {
  switch (field) {
    case "contact.name":
      return profile.contact.name || null;
    case "contact.email":
      return profile.contact.email;
    case "contact.phone":
      return profile.contact.phone;
    case "contact.location":
      return profile.contact.location;
    case "work_authorization.status":
      return profile.work_authorization.status;
    case "most_recent.title":
      return profile.experience[0]?.title ?? null;
    case "most_recent.company":
      return profile.experience[0]?.company ?? null;
    case "total_years_experience":
      return String(profile.total_years_experience);
    case "education.institution":
      return profile.education[0]?.institution ?? null;
    case "education.degree":
      return profile.education[0]?.degree ?? null;
    default:
      return null; // resume_file / cover_letter_file / essay / unknown handled by caller
  }
}

/** Pure function: given the resolved field mappings, the profile, and any
 * already-drafted essay answers (keyed by selector), produce the list of fill
 * actions. Nothing here touches the DOM or ever represents a submit action —
 * a FillAction is either "text"/"select"/"file"/"essay", nothing else exists. */
export function buildFillPlan(mappings: FieldMapping[], profile: ExtensionProfile, essayAnswers: Record<string, string>): FillAction[] {
  const actions: FillAction[] = [];

  for (const m of mappings) {
    if (m.confidence < FILL_CONFIDENCE_THRESHOLD) continue;

    if (m.profile_field === "resume_file") {
      actions.push({ selector: m.selector, kind: "file", value: "resume", source: m.profile_field });
      continue;
    }
    if (m.profile_field === "cover_letter_file") {
      actions.push({ selector: m.selector, kind: "file", value: "cover_letter", source: m.profile_field });
      continue;
    }
    if (m.profile_field === "essay") {
      const answer = essayAnswers[m.selector];
      if (answer) actions.push({ selector: m.selector, kind: "essay", value: answer, source: m.profile_field });
      continue;
    }
    if (m.profile_field === "unknown") continue;

    const value = resolveValue(m.profile_field, profile);
    if (value) actions.push({ selector: m.selector, kind: "text", value, source: m.profile_field });
  }

  return actions;
}
