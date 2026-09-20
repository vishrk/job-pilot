import type { FillAction } from "../types.ts";

const PANEL_ID = "jobpilot-review-panel";

/** Renders the pre-submit review panel (§7 Phase 3 accept criteria). This panel
 * has no button, link, or keyboard handler that submits the underlying form —
 * only a "Dismiss" control that hides the panel. Submitting is the user's own
 * click on the employer's own Submit button, off this extension's DOM entirely. */
export function showReviewPanel(actions: FillAction[], onEditEssay: (selector: string, newValue: string) => void) {
  document.getElementById(PANEL_ID)?.remove();

  const panel = document.createElement("div");
  panel.id = PANEL_ID;
  panel.style.cssText =
    "position:fixed;top:16px;right:16px;width:340px;max-height:80vh;overflow:auto;" +
    "background:#fff;border:2px solid #222;border-radius:8px;padding:12px;z-index:2147483647;" +
    "font-family:system-ui,sans-serif;font-size:13px;box-shadow:0 4px 16px rgba(0,0,0,.3)";

  const heading = document.createElement("div");
  heading.textContent = "JobPilot filled these fields — review, then click Submit yourself on the page.";
  heading.style.cssText = "font-weight:600;margin-bottom:8px";
  panel.appendChild(heading);

  for (const action of actions) {
    const row = document.createElement("div");
    row.style.cssText = "margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid #eee";

    const label = document.createElement("div");
    label.textContent = `${action.source}${action.kind === "essay" ? " (draft — edit before submitting)" : ""}`;
    label.style.cssText = "color:#666;font-size:11px";
    row.appendChild(label);

    if (action.kind === "essay") {
      const textarea = document.createElement("textarea");
      textarea.value = action.value;
      textarea.style.cssText = "width:100%;min-height:60px";
      textarea.addEventListener("input", () => onEditEssay(action.selector, textarea.value));
      row.appendChild(textarea);
    } else if (action.kind === "file") {
      const val = document.createElement("div");
      val.textContent = `[${action.value} file attached]`;
      row.appendChild(val);
    } else {
      const val = document.createElement("div");
      val.textContent = action.value;
      row.appendChild(val);
    }

    panel.appendChild(row);
  }

  const dismiss = document.createElement("button");
  dismiss.textContent = "Dismiss";
  dismiss.addEventListener("click", () => panel.remove());
  panel.appendChild(dismiss);

  document.body.appendChild(panel);
}
