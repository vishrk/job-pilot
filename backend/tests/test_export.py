"""Round-trip check for the DOCX exporter: every bullet/summary/skill that goes in
must come back out as extractable text. This covers the rendering half of the
Phase 2 accept criteria ("the exported file round-trips with no lost sections");
the other half — that our LLM profile extractor can re-parse it — needs a live
API key and is a manual acceptance step, not a unit test.
"""

from app.services.export import to_docx
from app.services.resume_parse import extract_text

CONTENT = {
    "summary": "Senior engineer with a track record of shipping scalable services.",
    "sections": [
        {
            "experience_id": "exp_01",
            "bullets": [
                {"id": "obl_1", "source_bullet_id": "blt_a1", "text": "Built a Python microservice handling 10K req/s"},
                {"id": "obl_2", "source_bullet_id": "blt_a2", "text": "Mentored 2 junior engineers"},
            ],
        }
    ],
    "skills": [{"canonical": "Python"}, {"canonical": "Kubernetes"}],
}


def test_docx_export_preserves_all_bullet_text():
    docx_bytes = to_docx(CONTENT, "resume")
    extracted = extract_text("resume.docx", docx_bytes)
    assert "Built a Python microservice handling 10K req/s" in extracted
    assert "Mentored 2 junior engineers" in extracted


def test_docx_export_preserves_summary_and_skills():
    docx_bytes = to_docx(CONTENT, "resume")
    extracted = extract_text("resume.docx", docx_bytes)
    assert CONTENT["summary"] in extracted
    assert "Python" in extracted and "Kubernetes" in extracted


if __name__ == "__main__":
    test_docx_export_preserves_all_bullet_text()
    test_docx_export_preserves_summary_and_skills()
    print("all export checks passed")
