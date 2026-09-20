import type { FormField } from "../types.ts";

type FillableElement = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;

function findLabel(el: FillableElement): string | null {
  if (el.id) {
    const byFor = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
    if (byFor?.textContent) return byFor.textContent.trim();
  }
  const wrappingLabel = el.closest("label");
  if (wrappingLabel?.textContent) return wrappingLabel.textContent.trim();
  const ariaLabel = el.getAttribute("aria-label");
  if (ariaLabel) return ariaLabel.trim();
  return el instanceof HTMLSelectElement ? null : el.placeholder || null;
}

function stableSelector(el: FillableElement, index: number): string {
  if (el.id) return `#${CSS.escape(el.id)}`;
  const generated = `jobpilot-field-${index}`;
  el.setAttribute("data-jobpilot-id", generated);
  return `[data-jobpilot-id="${generated}"]`;
}

/** Scans the page for fillable fields. DOM-facing and intentionally thin — the
 * actual mapping/fill-plan logic lives in fillPlan.ts, which is pure and unit
 * tested; this file just has no logic worth testing beyond "does it find inputs". */
export function scanForm(root: ParentNode = document): FormField[] {
  const elements = Array.from(root.querySelectorAll<FillableElement>("input, select, textarea"));
  return elements
    .filter((el) => !["hidden", "submit", "button", "reset"].includes((el as HTMLInputElement).type))
    .map((el, i) => ({
      selector: stableSelector(el, i),
      label: findLabel(el),
      field_type: el instanceof HTMLSelectElement ? "select" : el instanceof HTMLTextAreaElement ? "textarea" : el.type || "text",
      name_attr: el.getAttribute("name"),
      options:
        el instanceof HTMLSelectElement
          ? Array.from(el.options).map((o) => o.textContent?.trim() ?? "")
          : undefined,
    }));
}
