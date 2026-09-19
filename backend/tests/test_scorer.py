"""Golden set: hand-labeled (profile, job) pairs with expected score bands.

Scorer changes should surface as diffs against these bands, not silent drift.
Run: pytest backend/tests/test_scorer.py
"""

from datetime import date

from app.schemas.job import HardGates, JobRequirements, SkillRequirement
from app.schemas.profile import ContactInfo, ExperienceEntry, MasterProfile, SkillEntry, WorkAuthorization
from app.services.scorer import score

TODAY = date(2026, 9, 19)


def make_profile(skills, years, location="San Francisco, CA", work_auth="citizen"):
    return MasterProfile(
        contact=ContactInfo(name="Test User", location=location),
        work_authorization=WorkAuthorization(status=work_auth),
        experience=[
            ExperienceEntry(id="exp_01", company="Acme", title="Software Engineer", start_date="2018-01", end_date=None)
        ],
        skills=[
            SkillEntry(canonical=name, last_used=last_used, months_experience=months)
            for name, last_used, months in skills
        ],
        total_years_experience=years,
    )


def make_job(skills, *, seniority="mid", min_years=None, onsite="unspecified", locations=None, work_auth=None, domain_tags=None, jd_hash="x"):
    return JobRequirements(
        jd_hash=jd_hash,
        title_normalized="Software Engineer",
        seniority_level=seniority,
        domain_tags=domain_tags or [],
        skills=[SkillRequirement(canonical=name, weight=weight) for name, weight in skills],
        gates=HardGates(
            work_authorization=work_auth,
            onsite_policy=onsite,
            locations=locations,
            min_years_experience=min_years,
        ),
        raw_title="Software Engineer",
        extracted_at="2026-01-01T00:00:00",
    )


# (profile, job, expected_min, expected_max) — bands, not exact values
GOLDEN_SET = [
    (
        "perfect skill + recency + depth match",
        make_profile([("Python", "2026-08", 60), ("React", "2026-08", 48)], years=8),
        make_job([("Python", "required"), ("React", "required")], seniority="senior"),
        85, 100,
    ),
    (
        # skill_coverage/recency/depth all bottom out, but seniority_fit and the
        # neutral (no-embedding) domain_fit still contribute their full weight (0.20 + 0.15*0.5)
        "all required skills missing",
        make_profile([("Java", "2026-08", 60)], years=8),
        make_job([("Python", "required"), ("React", "required")], seniority="senior"),
        20, 35,
    ),
    (
        "half of required skills present",
        make_profile([("Python", "2026-08", 60)], years=8),
        make_job([("Python", "required"), ("React", "required")], seniority="senior"),
        45, 75,
    ),
    (
        "stale skill (last used 5y ago) still counts but discounted",
        make_profile([("Python", "2021-09", 60)], years=8),
        make_job([("Python", "required")], seniority="senior"),
        50, 85,
    ),
    (
        # depth is only 15% of the weighted sum, so even near-zero evidence (1 month)
        # doesn't crater the blended score while coverage/recency/seniority are maxed
        "shallow skill evidence stays high on the blended score (depth is a minority weight)",
        make_profile([("Python", "2026-08", 1)], years=8),
        make_job([("Python", "required")], seniority="senior"),
        65, 90,
    ),
    (
        # seniority_fit itself is heavily penalized (checked separately below); it just
        # doesn't dominate the blend on its own since it's 20% of the weighted sum
        "junior candidate on a staff-level job — under-qualified discount visible, not decisive",
        make_profile([("Python", "2026-08", 24)], years=2),
        make_job([("Python", "required")], seniority="staff"),
        55, 85,
    ),
    (
        "senior candidate on a junior job — mild over-qualified discount only",
        make_profile([("Python", "2026-08", 120)], years=12),
        make_job([("Python", "required")], seniority="junior"),
        60, 100,
    ),
    (
        "no skills stated on the job — skill_coverage is neutral (1.0)",
        make_profile([("Python", "2026-08", 60)], years=8),
        make_job([], seniority="senior"),
        60, 100,
    ),
    (
        "years-of-experience hard gate fails — job excluded, not just low-scored",
        make_profile([("Python", "2026-08", 60)], years=2),
        make_job([("Python", "required")], seniority="senior", min_years=8),
        None, None,
    ),
]


def test_golden_set_bands():
    failures = []
    for name, profile, job, lo, hi in GOLDEN_SET:
        result = score(profile, job, today=TODAY)
        if lo is None:
            if result["score"] is not None:
                failures.append(f"{name}: expected gated-out (None), got {result['score']}")
            continue
        s = result["score"]
        if s is None or not (lo <= s <= hi):
            failures.append(f"{name}: expected [{lo}, {hi}], got {s}")
    assert not failures, "\n".join(failures)


def test_determinism():
    _, profile, job, *_ = GOLDEN_SET[0]
    first = score(profile, job, today=TODAY)
    second = score(profile, job, today=TODAY)
    assert first == second


def test_hard_gate_excludes_not_lowers():
    profile = make_profile([("Python", "2026-08", 60)], years=8, work_auth="needs_sponsorship")
    job = make_job([("Python", "required")], work_auth=["citizen", "permanent_resident"])
    result = score(profile, job, today=TODAY)
    assert result["score"] is None
    assert result["gates"]["status"] == "needs_sponsorship"


def test_gate_breakdown_states_reason():
    profile = make_profile([("Python", "2026-08", 60)], years=2)
    job = make_job([("Python", "required")], min_years=8)
    result = score(profile, job, today=TODAY)
    failed = [c for c in result["gates"]["checks"] if not c["passed"]]
    assert failed and failed[0]["reason"]


def test_seniority_component_penalizes_underqualification_harder():
    """The blended score barely moves (seniority_fit is 20% of the weight), but the
    component itself must show the asymmetric penalty the spec requires (§2.3)."""
    profile = make_profile([("Python", "2026-08", 24)], years=2)
    under = score(profile, make_job([("Python", "required")], seniority="staff"), today=TODAY)
    over = score(profile, make_job([("Python", "required")], seniority="intern"), today=TODAY)
    assert under["components"]["seniority_fit"] < 0.2
    assert over["components"]["seniority_fit"] > under["components"]["seniority_fit"]


def test_depth_component_reflects_evidence_amount():
    shallow_profile = make_profile([("Python", "2026-08", 1)], years=8)
    deep_profile = make_profile([("Python", "2026-08", 60)], years=8)
    job = make_job([("Python", "required")], seniority="senior")
    shallow = score(shallow_profile, job, today=TODAY)
    deep = score(deep_profile, job, today=TODAY)
    assert shallow["components"]["depth"] < deep["components"]["depth"]


def test_preferred_skill_missing_costs_less_than_required_skill_missing():
    profile = make_profile([("Python", "2026-08", 24)], years=8)
    job_preferred_missing = make_job(
        [("Python", "required"), ("Go", "preferred")], seniority="senior", jd_hash="a"
    )
    job_required_missing = make_job(
        [("Python", "required"), ("Go", "required")], seniority="senior", jd_hash="b"
    )
    a = score(profile, job_preferred_missing, today=TODAY)
    b = score(profile, job_required_missing, today=TODAY)
    assert a["components"]["skill_coverage"] > b["components"]["skill_coverage"]


if __name__ == "__main__":
    test_golden_set_bands()
    test_determinism()
    test_hard_gate_excludes_not_lowers()
    test_gate_breakdown_states_reason()
    test_seniority_component_penalizes_underqualification_harder()
    test_depth_component_reflects_evidence_amount()
    test_preferred_skill_missing_costs_less_than_required_skill_missing()
    print("all scorer checks passed")
