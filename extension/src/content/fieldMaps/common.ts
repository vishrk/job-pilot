import type { FieldMapping, FormField, ProfileFieldPath } from "../../types.ts";

export type FieldMatcher = (field: FormField) => ProfileFieldPath | null;

/** Runs a deterministic matcher over every field; anything it can't classify
 * falls through to the backend form-mapper agent instead of being guessed at. */
export function applyDeterministicMap(fields: FormField[], matcher: FieldMatcher): { mapped: FieldMapping[]; unmapped: FormField[] } {
  const mapped: FieldMapping[] = [];
  const unmapped: FormField[] = [];

  for (const field of fields) {
    const profileField = matcher(field);
    if (profileField) {
      mapped.push({ selector: field.selector, profile_field: profileField, confidence: 1.0 });
    } else {
      unmapped.push(field);
    }
  }

  return { mapped, unmapped };
}

export function labelMatches(field: FormField, ...patterns: RegExp[]): boolean {
  const haystack = `${field.label ?? ""} ${field.name_attr ?? ""}`.toLowerCase();
  return patterns.some((p) => p.test(haystack));
}
