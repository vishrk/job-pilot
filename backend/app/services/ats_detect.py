"""Given a company domain, find which ATS it uses and its board token, by trying
the domain-derived slug against each adapter until one returns real postings.
"""

from app.services.adapters import ADAPTERS


def _candidate_slugs(domain: str) -> list[str]:
    base = domain.split(".")[0].lower()
    return [base, base.replace("-", ""), base.replace("_", "-")]


def detect(domain: str) -> tuple[str, str] | None:
    """Returns (ats_kind, board_token) or None if no adapter matches.

    # ponytail: a board with zero currently-open roles won't be detected (we require
    # a non-empty response as proof of match). Fine for v1 — re-run detection later
    # if a company is added and initially shows no listings.
    """
    for slug in _candidate_slugs(domain):
        for ats_kind, list_jobs in ADAPTERS.items():
            try:
                jobs = list_jobs(slug)
            except Exception:
                continue
            if jobs:
                return ats_kind, slug
    return None
