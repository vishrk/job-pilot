"""Form mapper — the one genuine agent loop in the system (§5). Fires only on an
unknown form (no cached FormMap for this domain+fingerprint); the result is cached
so the next user on the same form costs zero LLM calls (§7 Phase 3 accept criteria).

The loop: propose a mapping for every field in one pass, then take a second pass
only at the fields the model itself flagged as low-confidence, giving it the
already-resolved neighboring fields as extra context (a field next to a mapped
"City" field is more likely "State" than a stray guess). Two passes, not N,
because our target is a fixed field taxonomy (schemas/form.py) — there's no open-
ended tool use to do here, just disambiguation.
"""

from sqlalchemy.orm import Session

from app.llm.client import call_structured
from app.models import FormMap
from app.schemas.form import FieldMapping, FormField, FormMapResult

LOW_CONFIDENCE = 0.6

SYSTEM_PROMPT = """You map job application form fields to a fixed taxonomy of profile
fields, using each field's label, input type, and name attribute. Valid profile_field
values: contact.name, contact.email, contact.phone, contact.location,
work_authorization.status, most_recent.title, most_recent.company,
total_years_experience, education.institution, education.degree, resume_file (a file
upload for a resume/CV), cover_letter_file (a file upload for a cover letter), essay
(any free-text question that isn't one of the above — "why do you want to work here",
"describe a challenge you solved", years-of-experience-with-X questions, etc), or
unknown (you cannot tell what this field is for). Give a confidence 0..1 for each."""


def _fields_prompt(fields: list[FormField]) -> str:
    lines = []
    for f in fields:
        opts = f", options={f.options}" if f.options else ""
        lines.append(f"({f.selector}) type={f.field_type} label={f.label!r} name={f.name_attr!r}{opts}")
    return "\n".join(lines)


def _propose(db: Session, fields: list[FormField], user_id: str | None, extra_context: str = "") -> FormMapResult:
    prompt = _fields_prompt(fields)
    if extra_context:
        prompt = f"{extra_context}\n\nFields needing a second look:\n{prompt}"
    return call_structured(
        db,
        node="form_mapper",
        model="claude-sonnet-5",
        effort="medium",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        output_schema=FormMapResult,
        user_id=user_id,
    )


def _agent_loop(db: Session, fields: list[FormField], user_id: str | None) -> FormMapResult:
    first_pass = _propose(db, fields, user_id)
    by_selector = {m.selector: m for m in first_pass.mappings}

    uncertain_selectors = {m.selector for m in first_pass.mappings if m.confidence < LOW_CONFIDENCE}
    if uncertain_selectors:
        confident_context = "Already-resolved neighboring fields:\n" + "\n".join(
            f"({s}) -> {m.profile_field}" for s, m in by_selector.items() if s not in uncertain_selectors
        )
        uncertain_fields = [f for f in fields if f.selector in uncertain_selectors]
        second_pass = _propose(db, uncertain_fields, user_id, extra_context=confident_context)
        for m in second_pass.mappings:
            by_selector[m.selector] = m

    return FormMapResult(mappings=list(by_selector.values()))


def resolve_form(db: Session, *, domain: str, form_fingerprint: str, fields: list[FormField], user_id: str | None = None) -> FormMapResult:
    cached = db.query(FormMap).filter_by(domain=domain, form_fingerprint=form_fingerprint).first()
    if cached and cached.health != "broken":
        return FormMapResult(mappings=[FieldMapping(**m) for m in cached.mapping_json["mappings"]])

    result = _agent_loop(db, fields, user_id)

    if cached:
        cached.mapping_json = result.model_dump()
        cached.health = "untested"
    else:
        db.add(FormMap(domain=domain, form_fingerprint=form_fingerprint, mapping_json=result.model_dump()))
    db.commit()
    return result
