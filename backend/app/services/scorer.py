"""Deterministic match scoring — no LLM calls. See project brief §2.3.

Stage 0: hard gates (pass / fail / needs_sponsorship), Stage 1: five 0..1
components, Stage 2: weighted sum -> 0..100. Same (profile, job) always
gives the same score.
"""

import math
from datetime import date

from app.schemas.job import JobRequirements
from app.schemas.profile import MasterProfile

SENIORITY_RANK = {
    "intern": 0,
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "staff": 4,
    "principal": 5,
    "exec": 6,
}

# ponytail: single weight set for Phase 0 — no job-family calibration data
# exists yet. Add a per-family table once matches -> outcomes gives us
# something to fit against (§7 Phase 5 outcome loop).
WEIGHTS = {
    "skill_coverage": 0.35,
    "recency": 0.15,
    "depth": 0.15,
    "seniority_fit": 0.20,
    "domain_fit": 0.15,
}

RECENCY_HALF_LIFE_YEARS = 5.0
DEPTH_CEILING_MONTHS = 60  # 5 years of evidence = full depth score


def _skill_weight(weight: str) -> int:
    return 3 if weight == "required" else 1


def _years_since(yyyymm: str | None, today: date) -> float | None:
    if not yyyymm:
        return None
    year, month = int(yyyymm[:4]), int(yyyymm[5:7])
    return (today.year - year) + (today.month - month) / 12


def check_gates(profile: MasterProfile, job: JobRequirements) -> dict:
    checks = []

    if job.gates.work_authorization:
        ok = profile.work_authorization.status in job.gates.work_authorization
        needs_sponsorship = (
            not ok
            and profile.work_authorization.status == "needs_sponsorship"
            and "needs_sponsorship" not in job.gates.work_authorization
        )
        checks.append(
            {
                "gate": "work_authorization",
                "passed": ok,
                "needs_sponsorship": needs_sponsorship,
                "reason": None if ok else f"Job requires one of {job.gates.work_authorization}",
            }
        )

    if job.gates.onsite_policy in ("onsite", "hybrid") and job.gates.locations:
        location = (profile.contact.location or "").lower()
        ok = any(loc.lower() in location or location in loc.lower() for loc in job.gates.locations)
        checks.append(
            {
                "gate": "location",
                "passed": ok,
                "reason": None if ok else f"Job requires location in {job.gates.locations}",
            }
        )

    for field, label in (("required_license", "license"), ("required_clearance", "clearance")):
        required = getattr(job.gates, field)
        if required:
            haystack = " ".join(
                [*(t for b in profile.bullets for t in b.tags), *(s.canonical for s in profile.skills)]
            ).lower()
            ok = required.lower() in haystack
            checks.append(
                {"gate": label, "passed": ok, "reason": None if ok else f"Requires {required}, not found in profile"}
            )

    if job.gates.min_years_experience is not None:
        ok = profile.total_years_experience >= job.gates.min_years_experience
        checks.append(
            {
                "gate": "min_years_experience",
                "passed": ok,
                "reason": None
                if ok
                else f"Requires {job.gates.min_years_experience}y, profile has {profile.total_years_experience}y",
            }
        )

    failed = [c for c in checks if not c["passed"]]
    if not failed:
        status = "pass"
    elif any(c.get("needs_sponsorship") for c in failed):
        status = "needs_sponsorship"
    else:
        status = "fail"

    return {"status": status, "checks": checks}


def skill_coverage(profile: MasterProfile, job: JobRequirements) -> float:
    if not job.skills:
        return 1.0
    profile_skills = {s.canonical for s in profile.skills}
    total = sum(_skill_weight(s.weight) for s in job.skills)
    matched = sum(_skill_weight(s.weight) for s in job.skills if s.canonical in profile_skills)
    return matched / total if total else 1.0


def recency(profile: MasterProfile, job: JobRequirements, today: date | None = None) -> float:
    today = today or date.today()
    profile_by_skill = {s.canonical: s for s in profile.skills}
    if not job.skills:
        return 1.0
    k = math.log(2) / RECENCY_HALF_LIFE_YEARS
    total_weight, weighted_sum = 0, 0.0
    for req in job.skills:
        w = _skill_weight(req.weight)
        total_weight += w
        skill = profile_by_skill.get(req.canonical)
        if skill is None:
            continue
        years = _years_since(skill.last_used, today)
        decay = math.exp(-k * years) if years is not None else 0.5
        weighted_sum += w * decay
    return weighted_sum / total_weight if total_weight else 1.0


def depth(profile: MasterProfile, job: JobRequirements) -> float:
    profile_by_skill = {s.canonical: s for s in profile.skills}
    if not job.skills:
        return 1.0
    ceiling = math.log(1 + DEPTH_CEILING_MONTHS)
    total_weight, weighted_sum = 0, 0.0
    for req in job.skills:
        w = _skill_weight(req.weight)
        total_weight += w
        skill = profile_by_skill.get(req.canonical)
        if skill is None or skill.months_experience is None:
            continue
        weighted_sum += w * min(math.log(1 + skill.months_experience) / ceiling, 1.0)
    return weighted_sum / total_weight if total_weight else 1.0


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def _infer_profile_seniority_rank(profile: MasterProfile) -> int:
    years = profile.total_years_experience
    if years < 1:
        return SENIORITY_RANK["intern"]
    if years < 3:
        return SENIORITY_RANK["junior"]
    if years < 6:
        return SENIORITY_RANK["mid"]
    if years < 10:
        return SENIORITY_RANK["senior"]
    if years < 14:
        return SENIORITY_RANK["staff"]
    return SENIORITY_RANK["principal"]


def seniority_fit(profile: MasterProfile, job: JobRequirements, title_embeddings: tuple[list[float], list[float]] | None = None) -> float:
    """Asymmetric: under-qualified is penalized harder than over-qualified."""
    job_rank = SENIORITY_RANK[job.seniority_level]
    profile_rank = _infer_profile_seniority_rank(profile)
    diff = job_rank - profile_rank
    if diff > 0:  # under-qualified
        rank_score = max(0.0, 1 - diff * 0.3)
    else:  # at or over-qualified
        rank_score = max(0.7, 1 - abs(diff) * 0.1)

    if title_embeddings is None:
        return rank_score

    profile_vec, job_vec = title_embeddings
    cos_score = (_cosine(profile_vec, job_vec) + 1) / 2  # map [-1,1] -> [0,1]
    return 0.5 * rank_score + 0.5 * cos_score


def domain_fit(domain_embeddings: tuple[list[float], list[float]] | None) -> float:
    if domain_embeddings is None:
        return 0.5  # neutral when we couldn't embed either side
    profile_vec, job_vec = domain_embeddings
    return (_cosine(profile_vec, job_vec) + 1) / 2


def score(
    profile: MasterProfile,
    job: JobRequirements,
    *,
    title_embeddings: tuple[list[float], list[float]] | None = None,
    domain_embeddings: tuple[list[float], list[float]] | None = None,
    today: date | None = None,
    job_family: str = "default",
) -> dict:
    gates = check_gates(profile, job)
    if gates["status"] != "pass":
        return {"score": None, "gates": gates, "components": {}}

    components = {
        "skill_coverage": skill_coverage(profile, job),
        "recency": recency(profile, job, today),
        "depth": depth(profile, job),
        "seniority_fit": seniority_fit(profile, job, title_embeddings),
        "domain_fit": domain_fit(domain_embeddings),
    }
    weights = WEIGHTS  # job_family table doesn't exist yet, see WEIGHTS comment
    final_score = 100 * sum(weights[c] * v for c, v in components.items())
    return {"score": round(final_score, 2), "gates": gates, "components": components}
