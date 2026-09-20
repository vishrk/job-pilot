import { test } from "node:test";
import assert from "node:assert/strict";
import { fingerprint } from "./fingerprint.ts";
import type { FormField } from "../types.ts";

test("same field structure produces the same fingerprint", async () => {
  const fields: FormField[] = [{ selector: "#a", label: "Email", field_type: "email", name_attr: "email" }];
  assert.equal(await fingerprint(fields), await fingerprint(fields));
});

test("field order changes the fingerprint", async () => {
  const a: FormField[] = [
    { selector: "#a", label: "First name", field_type: "text", name_attr: "first" },
    { selector: "#b", label: "Last name", field_type: "text", name_attr: "last" },
  ];
  const b = [...a].reverse();
  assert.notEqual(await fingerprint(a), await fingerprint(b));
});

test("selector does not affect the fingerprint — only type/label/name", async () => {
  const a: FormField[] = [{ selector: "#field-17", label: "Email", field_type: "email", name_attr: "email" }];
  const b: FormField[] = [{ selector: "#field-99", label: "Email", field_type: "email", name_attr: "email" }];
  assert.equal(await fingerprint(a), await fingerprint(b));
});

test("matches the backend's Python fingerprint byte-for-byte for the same input", async () => {
  // Computed via: backend/.venv/Scripts/python.exe -c
  //   "from app.schemas.form import FormField; from app.services.form_fingerprint import fingerprint;
  //    print(fingerprint([FormField(selector='#a', label='Email', field_type='email', name_attr='email')]))"
  const EXPECTED_FROM_PYTHON = "bec2714a17fbd31b8a96b749825d939709da977ad4da6b4780a66dae934e9ec8";
  const fields: FormField[] = [{ selector: "#a", label: "Email", field_type: "email", name_attr: "email" }];
  assert.equal(await fingerprint(fields), EXPECTED_FROM_PYTHON);
});
