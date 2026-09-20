// The extension must never submit a form on the user's behalf (§2.1, §7 Phase 3
// accept criteria: "No code path exists that can trigger the form's submit
// action"). Rather than trust a unit test of today's fill logic, this statically
// scans every source file for the actual browser APIs that would submit a form
// or fire a click on a submit control, so the guarantee holds even as the fill
// logic changes later.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

const SRC_DIR = path.join(import.meta.dirname, "..", "src");

const FORBIDDEN_PATTERNS: [RegExp, string][] = [
  [/\.submit\s*\(/, ".submit() call"],
  [/\.requestSubmit\s*\(/, ".requestSubmit() call"],
  [/type\s*===\s*["']submit["']\s*\)[^;]*\.click/, "click() on a submit-typed element"],
  [/dispatchEvent\([^)]*["']submit["']/, "dispatchEvent of a submit event"],
];

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
}

function allSourceFiles(dir: string): string[] {
  const entries = readdirSync(dir);
  const files: string[] = [];
  for (const entry of entries) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) {
      files.push(...allSourceFiles(full));
    } else if (/\.(ts|tsx)$/.test(entry) && !entry.endsWith(".test.ts")) {
      files.push(full);
    }
  }
  return files;
}

test("no source file contains a form-submit trigger", () => {
  const files = allSourceFiles(SRC_DIR);
  assert.ok(files.length > 0, "expected to find source files to scan");

  const violations: string[] = [];
  for (const file of files) {
    const content = stripComments(readFileSync(file, "utf-8"));
    for (const [pattern, description] of FORBIDDEN_PATTERNS) {
      if (pattern.test(content)) {
        violations.push(`${path.relative(SRC_DIR, file)}: ${description}`);
      }
    }
  }

  assert.deepEqual(violations, []);
});

test("the review panel creates no button whose own label is 'Submit'", () => {
  // The panel's instructional copy legitimately says "click Submit yourself" —
  // what it must never have is a button/control OF ITS OWN that performs that
  // action. Its only button is the "Dismiss" one.
  const reviewPanelSource = readFileSync(path.join(SRC_DIR, "content", "reviewPanel.ts"), "utf-8");
  const buttonLabels = [...reviewPanelSource.matchAll(/\.textContent\s*=\s*["']([^"']+)["']/g)].map((m) => m[1]);
  const submitLabels = buttonLabels.filter((label) => /^submit$/i.test(label.trim()));
  assert.deepEqual(submitLabels, []);
});
