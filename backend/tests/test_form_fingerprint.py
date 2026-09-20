from app.schemas.form import FormField
from app.services.form_fingerprint import fingerprint


def test_same_structure_same_fingerprint():
    fields = [FormField(selector="#a", label="Email", field_type="email", name_attr="email")]
    assert fingerprint(fields) == fingerprint(fields)


def test_different_field_order_changes_fingerprint():
    a = [
        FormField(selector="#a", label="First name", field_type="text", name_attr="first"),
        FormField(selector="#b", label="Last name", field_type="text", name_attr="last"),
    ]
    b = list(reversed(a))
    assert fingerprint(a) != fingerprint(b)


def test_selector_does_not_affect_fingerprint():
    """Runtime DOM ids shouldn't matter — only type/label/name, which are stable
    across page loads even if the generated selector changes."""
    a = [FormField(selector="#field-17", label="Email", field_type="email", name_attr="email")]
    b = [FormField(selector="#field-99", label="Email", field_type="email", name_attr="email")]
    assert fingerprint(a) == fingerprint(b)


def test_different_label_changes_fingerprint():
    a = [FormField(selector="#a", label="Email", field_type="email", name_attr="email")]
    b = [FormField(selector="#a", label="Personal Email", field_type="email", name_attr="email")]
    assert fingerprint(a) != fingerprint(b)


if __name__ == "__main__":
    test_same_structure_same_fingerprint()
    test_different_field_order_changes_fingerprint()
    test_selector_does_not_affect_fingerprint()
    test_different_label_changes_fingerprint()
    print("all form_fingerprint checks passed")
