import { test } from "node:test";
import assert from "node:assert/strict";
import { buildFillPlan } from "./fillPlan.ts";
import type { ExtensionProfile, FieldMapping } from "../types.ts";

const PROFILE: ExtensionProfile = {
  contact: { name: "Ada Lovelace", email: "ada@example.com", phone: "555-1234", location: "London, UK" },
  work_authorization: { status: "citizen" },
  experience: [{ title: "Senior Engineer", company: "Acme" }],
  education: [{ institution: "Cambridge", degree: "Mathematics" }],
  total_years_experience: 8,
};

test("maps a confident text field to its profile value", () => {
  const mappings: FieldMapping[] = [{ selector: "#email", profile_field: "contact.email", confidence: 0.95 }];
  const actions = buildFillPlan(mappings, PROFILE, {});
  assert.deepEqual(actions, [{ selector: "#email", kind: "text", value: "ada@example.com", source: "contact.email" }]);
});

test("skips a field below the confidence threshold — leaves it for the user", () => {
  const mappings: FieldMapping[] = [{ selector: "#mystery", profile_field: "contact.phone", confidence: 0.4 }];
  const actions = buildFillPlan(mappings, PROFILE, {});
  assert.deepEqual(actions, []);
});

test("skips 'unknown' fields entirely", () => {
  const mappings: FieldMapping[] = [{ selector: "#x", profile_field: "unknown", confidence: 1.0 }];
  assert.deepEqual(buildFillPlan(mappings, PROFILE, {}), []);
});

test("resume_file and cover_letter_file become file actions, not text", () => {
  const mappings: FieldMapping[] = [
    { selector: "#resume", profile_field: "resume_file", confidence: 1.0 },
    { selector: "#cl", profile_field: "cover_letter_file", confidence: 1.0 },
  ];
  const actions = buildFillPlan(mappings, PROFILE, {});
  assert.deepEqual(actions, [
    { selector: "#resume", kind: "file", value: "resume", source: "resume_file" },
    { selector: "#cl", kind: "file", value: "cover_letter", source: "cover_letter_file" },
  ]);
});

test("essay field only fills if an answer was already drafted", () => {
  const mappings: FieldMapping[] = [{ selector: "#why", profile_field: "essay", confidence: 1.0 }];
  assert.deepEqual(buildFillPlan(mappings, PROFILE, {}), []); // no answer drafted yet
  const withAnswer = buildFillPlan(mappings, PROFILE, { "#why": "I love building things." });
  assert.deepEqual(withAnswer, [{ selector: "#why", kind: "essay", value: "I love building things.", source: "essay" }]);
});

test("skips a field whose profile value is missing (e.g. no education on file)", () => {
  const noEducation: ExtensionProfile = { ...PROFILE, education: [] };
  const mappings: FieldMapping[] = [{ selector: "#school", profile_field: "education.institution", confidence: 1.0 }];
  assert.deepEqual(buildFillPlan(mappings, noEducation, {}), []);
});

test("most_recent.title/company read from the first experience entry", () => {
  const mappings: FieldMapping[] = [
    { selector: "#title", profile_field: "most_recent.title", confidence: 1.0 },
    { selector: "#company", profile_field: "most_recent.company", confidence: 1.0 },
  ];
  const actions = buildFillPlan(mappings, PROFILE, {});
  assert.deepEqual(actions, [
    { selector: "#title", kind: "text", value: "Senior Engineer", source: "most_recent.title" },
    { selector: "#company", kind: "text", value: "Acme", source: "most_recent.company" },
  ]);
});
