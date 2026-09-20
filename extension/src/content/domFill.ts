import type { FillAction } from "../types.ts";

function setNativeValue(el: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
  setter?.call(el, value);
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
}

function fillFile(el: HTMLInputElement, file: File) {
  const transfer = new DataTransfer();
  transfer.items.add(file);
  el.files = transfer.files;
  el.dispatchEvent(new Event("change", { bubbles: true }));
}

/** Re-applies a single edited value (from the review panel's essay textarea) to
 * the actual underlying form field, so editing the draft in the panel updates
 * what the user will actually submit. */
export function updateFilledField(selector: string, value: string) {
  const el = document.querySelector(selector);
  if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) setNativeValue(el, value);
}

/** Applies a fill plan to the live DOM. This function — and this whole file —
 * never calls .submit(), .requestSubmit(), or .click() on anything. Filling the
 * form is as far as the extension goes; the human clicks Submit (§2.1). Enforced
 * by tests/no-submit.test.ts, which statically scans this directory for those
 * calls so the guarantee survives future edits, not just today's code. */
export function applyFillPlan(actions: FillAction[], files: { resume?: File; cover_letter?: File }) {
  for (const action of actions) {
    const el = document.querySelector(action.selector);
    if (!el) continue;

    if (action.kind === "file" && el instanceof HTMLInputElement) {
      const file = action.value === "resume" ? files.resume : files.cover_letter;
      if (file) fillFile(el, file);
      continue;
    }
    if ((action.kind === "text" || action.kind === "essay") && (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement)) {
      setNativeValue(el, action.value);
      continue;
    }
    if (action.kind === "text" && el instanceof HTMLSelectElement) {
      const option = Array.from(el.options).find((o) => o.textContent?.trim().toLowerCase() === action.value.toLowerCase());
      if (option) {
        el.value = option.value;
        el.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }
  }
}
