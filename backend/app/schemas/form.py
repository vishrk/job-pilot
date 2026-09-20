from typing import Literal

from pydantic import BaseModel

# The fixed set of things a form field can resolve to. "essay" routes to the answer
# library / essay answerer instead of a direct profile lookup; "unknown" means the
# agent couldn't confidently map it and the extension leaves it for the user.
ProfileFieldPath = Literal[
    "contact.name",
    "contact.email",
    "contact.phone",
    "contact.location",
    "work_authorization.status",
    "most_recent.title",
    "most_recent.company",
    "total_years_experience",
    "education.institution",
    "education.degree",
    "resume_file",
    "cover_letter_file",
    "essay",
    "unknown",
]


class FormField(BaseModel):
    selector: str  # stable selector the content script generated, e.g. "#field-17"
    label: str | None = None
    field_type: str  # "text" | "email" | "tel" | "select" | "textarea" | "file" | "radio" | "checkbox"
    name_attr: str | None = None
    options: list[str] | None = None


class FieldMapping(BaseModel):
    selector: str
    profile_field: ProfileFieldPath
    confidence: float


class FormMapResult(BaseModel):
    mappings: list[FieldMapping]
