import { applyFillPlan, updateFilledField } from "./domFill.ts";
import { matchGreenhouseField } from "./fieldMaps/greenhouse.ts";
import { matchLeverField } from "./fieldMaps/lever.ts";
import { applyDeterministicMap } from "./fieldMaps/common.ts";
import { buildFillPlan } from "./fillPlan.ts";
import { fingerprint } from "./fingerprint.ts";
import { showReviewPanel } from "./reviewPanel.ts";
import { scanForm } from "./scan.ts";
import type { ExtensionProfile, FieldMapping } from "../types.ts";

function sendMessage<T>(message: unknown): Promise<T> {
  return chrome.runtime.sendMessage(message);
}

function detectDeterministicMatcher(domain: string) {
  if (domain.includes("greenhouse.io")) return matchGreenhouseField;
  if (domain.includes("lever.co")) return matchLeverField;
  return null;
}

/** Orchestration only — every actual decision (what to fill, how to map a field)
 * lives in the pure/tested modules this calls into. Nothing in this file, or
 * anything it calls, ever triggers form submission (see domFill.ts and
 * tests/no-submit.test.ts). */
async function run() {
  const domain = window.location.hostname;
  const fields = scanForm();
  if (fields.length === 0) return;

  const matcher = detectDeterministicMatcher(domain);
  const { mapped, unmapped } = matcher ? applyDeterministicMap(fields, matcher) : { mapped: [] as FieldMapping[], unmapped: fields };

  let allMappings = mapped;
  if (unmapped.length > 0) {
    const formFingerprint = await fingerprint(unmapped);
    const resolved = await sendMessage<{ ok: boolean; result?: { mappings: FieldMapping[] } }>({
      type: "resolveForm",
      domain,
      formFingerprint,
      fields: unmapped,
    });
    if (resolved.ok && resolved.result) allMappings = [...mapped, ...resolved.result.mappings];
  }

  const sessionRes = await sendMessage<{ ok: boolean; session: { profile: ExtensionProfile } | null }>({ type: "getSession" });
  if (!sessionRes.ok || !sessionRes.session) return; // not logged in — nothing to fill with

  const essayFields = allMappings.filter((m) => m.profile_field === "essay");
  const essayAnswers: Record<string, string> = {};
  for (const m of essayFields) {
    const field = fields.find((f) => f.selector === m.selector);
    if (!field?.label) continue;
    const answer = await sendMessage<{ ok: boolean; answer?: string }>({ type: "resolveAnswer", question: field.label });
    if (answer.ok && answer.answer) essayAnswers[m.selector] = answer.answer;
  }

  const actions = buildFillPlan(allMappings, sessionRes.session.profile, essayAnswers);
  if (actions.length === 0) return;

  applyFillPlan(actions, {}); // resume/cover-letter File objects: TODO wire from popup document picker
  showReviewPanel(actions, (selector, newValue) => {
    const action = actions.find((a) => a.selector === selector);
    if (action) action.value = newValue;
    updateFilledField(selector, newValue);
  });
}

run();
