from app.schemas.profile import ContactInfo, MasterProfile, ProfileBullet, WorkAuthorization
from app.services.cover_letter import _DraftLetter, _DraftParagraph, strip_unknown_citations


def make_profile():
    return MasterProfile(
        contact=ContactInfo(name="Test User"),
        work_authorization=WorkAuthorization(status="citizen"),
        bullets=[ProfileBullet(id="blt_a1", experience_id="exp_01", text="Built a Python microservice handling 10K req/s")],
    )


def test_valid_citation_is_kept():
    profile = make_profile()
    draft = _DraftLetter(
        greeting="Dear Hiring Manager,",
        paragraphs=[_DraftParagraph(text="I built a high-throughput service.", source_bullet_ids=["blt_a1"])],
        closing="Sincerely,",
    )
    result = strip_unknown_citations(draft, profile)
    assert result["content"]["paragraphs"][0]["source_bullet_ids"] == ["blt_a1"]
    assert result["rejected_bullets"] == []


def test_fabricated_citation_is_stripped_but_text_kept_for_verifier_to_catch():
    profile = make_profile()
    draft = _DraftLetter(
        greeting="Dear Hiring Manager,",
        paragraphs=[_DraftParagraph(text="I generated $5M in revenue.", source_bullet_ids=["blt_fake"])],
        closing="Sincerely,",
    )
    result = strip_unknown_citations(draft, profile)
    assert result["content"]["paragraphs"][0]["source_bullet_ids"] == []
    assert result["content"]["paragraphs"][0]["text"] == "I generated $5M in revenue."  # not silently dropped, see module docstring
    assert result["rejected_bullets"][0]["reason"].startswith("unknown source_bullet_id")


if __name__ == "__main__":
    test_valid_citation_is_kept()
    test_fabricated_citation_is_stripped_but_text_kept_for_verifier_to_catch()
    print("all cover_letter checks passed")
