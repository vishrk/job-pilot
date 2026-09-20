"""Same algorithm as extension/src/content/fingerprint.ts — an ordered hash of
field type/label/name, so a form's structure (not its runtime DOM ids) determines
its identity. Kept here too so backend tests can construct realistic FormMap cache
keys without needing the extension build.
"""

import hashlib

from app.schemas.form import FormField


def fingerprint(fields: list[FormField]) -> str:
    parts = [f"{f.field_type}|{f.label or ''}|{f.name_attr or ''}" for f in fields]
    return hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()
