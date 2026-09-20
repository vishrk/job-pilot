"""Adversarial tests for the anti-fabrication gate (§2.4). These construct LLM
drafts by hand — including ones a misbehaving/hallucinating model plausibly
could produce — and check the pure enforce_provenance() function actually
rejects what it should, not just that happy-path output looks right.
"""

from app.schemas.job import HardGates, JobRequirements, SkillRequirement
from app.schemas.profile import ContactInfo, ExperienceEntry, MasterProfile, ProfileBullet, SkillEntry, WorkAuthorization
from app.services.tailor import _DraftBullet, _DraftSection, _TailorDraft, enforce_provenance


def make_profile():
    return MasterProfile(
        contact=ContactInfo(name="Test User"),
        work_authorization=WorkAuthorization(status="citizen"),
        experience=[
            ExperienceEntry(id="exp_01", company="Acme", title="Software Engineer", start_date="2018-01", end_date="2021-01"),
            ExperienceEntry(id="exp_02", company="Globex", title="Senior Software Engineer", start_date="2021-02", end_date=None),
        ],
        bullets=[
            ProfileBullet(id="blt_a1", experience_id="exp_01", text="Built a Python microservice handling 10K req/s"),
            ProfileBullet(id="blt_a2", experience_id="exp_01", text="Mentored 2 junior engineers"),
            ProfileBullet(id="blt_b1", experience_id="exp_02", text="Led migration to Kubernetes for 30 services"),
        ],
        skills=[SkillEntry(canonical="Python"), SkillEntry(canonical="Kubernetes"), SkillEntry(canonical="Go")],
        total_years_experience=6,
    )


def make_job():
    return JobRequirements(
        jd_hash="x",
        title_normalized="Senior Software Engineer",
        seniority_level="senior",
        skills=[SkillRequirement(canonical="Python", weight="required"), SkillRequirement(canonical="Kubernetes", weight="required")],
        gates=HardGates(),
        raw_title="Senior Software Engineer",
        extracted_at="2026-01-01T00:00:00",
    )


def test_valid_bullet_is_kept_with_correct_provenance():
    profile, job = make_profile(), make_job()
    draft = _TailorDraft(
        summary="Experienced engineer.",
        sections=[_DraftSection(experience_id="exp_01", bullets=[_DraftBullet(source_bullet_id="blt_a1", text="Built a Python microservice handling 10K req/s")])],
    )
    result = enforce_provenance(draft, profile, job)
    assert len(result["rejected_bullets"]) == 0
    kept = result["content"]["sections"][0]["bullets"][0]
    assert kept["source_bullet_id"] == "blt_a1"
    assert result["provenance_map"][kept["id"]] == "blt_a1"


def test_fabricated_source_bullet_id_is_rejected():
    """A hallucinated id that doesn't exist anywhere in the profile."""
    profile, job = make_profile(), make_job()
    draft = _TailorDraft(
        summary="Experienced engineer.",
        sections=[_DraftSection(experience_id="exp_01", bullets=[_DraftBullet(source_bullet_id="blt_does_not_exist", text="Shipped a $2M revenue feature")])],
    )
    result = enforce_provenance(draft, profile, job)
    assert result["content"]["sections"] == []  # nothing survived, no empty section rendered
    assert len(result["rejected_bullets"]) == 1
    assert result["rejected_bullets"][0]["reason"].startswith("unknown source_bullet_id")


def test_bullet_attributed_to_wrong_experience_is_rejected():
    """A real bullet id, but the model claims it belongs to a different role —
    a subtler fabrication than an outright invented id."""
    profile, job = make_profile(), make_job()
    draft = _TailorDraft(
        summary="Experienced engineer.",
        # blt_b1 actually belongs to exp_02, not exp_01
        sections=[_DraftSection(experience_id="exp_01", bullets=[_DraftBullet(source_bullet_id="blt_b1", text="Led migration to Kubernetes for 30 services")])],
    )
    result = enforce_provenance(draft, profile, job)
    assert result["content"]["sections"] == []
    assert result["rejected_bullets"][0]["reason"] == "source bullet belongs to a different experience entry"


def test_mixed_section_keeps_valid_and_drops_fabricated():
    profile, job = make_profile(), make_job()
    draft = _TailorDraft(
        summary="Experienced engineer.",
        sections=[
            _DraftSection(
                experience_id="exp_01",
                bullets=[
                    _DraftBullet(source_bullet_id="blt_a1", text="Built a Python microservice handling 10K req/s"),
                    _DraftBullet(source_bullet_id="blt_fake", text="Grew team revenue by 300%"),
                ],
            )
        ],
    )
    result = enforce_provenance(draft, profile, job)
    assert len(result["content"]["sections"][0]["bullets"]) == 1
    assert len(result["rejected_bullets"]) == 1


def test_skills_are_always_a_subset_of_master_skills():
    """The model's draft schema has no skills field at all — this checks the
    Python-computed skills list never contains anything outside the master profile,
    regardless of what job requirements ask for."""
    profile, job = make_profile(), make_job()
    draft = _TailorDraft(summary="x", sections=[])
    result = enforce_provenance(draft, profile, job)
    master_skills = {s.canonical for s in profile.skills}
    output_skills = {s["canonical"] for s in result["content"]["skills"]}
    assert output_skills <= master_skills
    assert output_skills == master_skills  # nothing dropped either, just reordered


def test_draft_schema_has_no_skills_field_for_model_to_write():
    """Structural guarantee, not just post-hoc filtering: even if a misbehaving
    model's JSON includes a 'skills' key, the Pydantic schema has no such field
    and Pydantic drops unknown keys by default — it can never reach the output."""
    parsed = _TailorDraft.model_validate({"summary": "x", "sections": [], "skills": ["Rust", "Made-up Skill"]})
    assert not hasattr(parsed, "skills")


if __name__ == "__main__":
    test_valid_bullet_is_kept_with_correct_provenance()
    test_fabricated_source_bullet_id_is_rejected()
    test_bullet_attributed_to_wrong_experience_is_rejected()
    test_mixed_section_keeps_valid_and_drops_fabricated()
    test_skills_are_always_a_subset_of_master_skills()
    test_draft_schema_has_no_skills_field_for_model_to_write()
    print("all tailor provenance checks passed")
