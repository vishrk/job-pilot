"""The agent loop's merge logic, tested with the LLM call stubbed out — this
checks the control flow (when does a second pass fire, does it correctly override
only the uncertain fields) without needing a live API key.
"""

from app.schemas.form import FieldMapping, FormField, FormMapResult
from app.services import form_mapper


def test_no_second_pass_when_all_confident(monkeypatch):
    calls = []

    def fake_propose(db, fields, user_id, extra_context=""):
        calls.append(extra_context)
        return FormMapResult(mappings=[FieldMapping(selector=f.selector, profile_field="contact.email", confidence=0.95) for f in fields])

    monkeypatch.setattr(form_mapper, "_propose", fake_propose)
    fields = [FormField(selector="#a", label="Email", field_type="email")]
    result = form_mapper._agent_loop(None, fields, None)

    assert len(calls) == 1  # only the first pass ran
    assert result.mappings[0].confidence == 0.95


def test_second_pass_only_for_uncertain_fields(monkeypatch):
    call_field_selectors = []

    def fake_propose(db, fields, user_id, extra_context=""):
        call_field_selectors.append([f.selector for f in fields])
        if not extra_context:
            return FormMapResult(
                mappings=[
                    FieldMapping(selector="#a", profile_field="contact.email", confidence=0.95),
                    FieldMapping(selector="#b", profile_field="unknown", confidence=0.2),
                ]
            )
        # second pass: refine the uncertain one using neighbor context
        return FormMapResult(mappings=[FieldMapping(selector="#b", profile_field="contact.phone", confidence=0.9)])

    monkeypatch.setattr(form_mapper, "_propose", fake_propose)
    fields = [
        FormField(selector="#a", label="Email", field_type="email"),
        FormField(selector="#b", label="Contact", field_type="tel"),
    ]
    result = form_mapper._agent_loop(None, fields, None)

    assert len(call_field_selectors) == 2
    assert call_field_selectors[1] == ["#b"]  # second pass only re-asked about the uncertain field
    by_selector = {m.selector: m for m in result.mappings}
    assert by_selector["#a"].profile_field == "contact.email"  # confident field untouched
    assert by_selector["#b"].profile_field == "contact.phone"  # uncertain field got refined
    assert by_selector["#b"].confidence == 0.9


if __name__ == "__main__":
    class _FakeMonkeypatch:
        def setattr(self, obj, name, value):
            setattr(obj, name, value)

    test_no_second_pass_when_all_confident(_FakeMonkeypatch())
    test_second_pass_only_for_uncertain_fields(_FakeMonkeypatch())
    print("all form_mapper checks passed")
