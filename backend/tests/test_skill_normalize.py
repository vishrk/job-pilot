"""Unit test for the pure cosine-similarity math in skill_normalize. The alias-table
lookup and embedding fallback need a live DB + Voyage key — covered by the Phase 0
manual acceptance run (real resume, real companies), not here.
"""

from app.services.skill_normalize import _cosine


def test_cosine_identical_vectors_is_one():
    v = [1.0, 2.0, 3.0]
    assert abs(_cosine(v, v) - 1.0) < 1e-9


def test_cosine_orthogonal_vectors_is_zero():
    assert abs(_cosine([1.0, 0.0], [0.0, 1.0])) < 1e-9


def test_cosine_opposite_vectors_is_negative_one():
    assert abs(_cosine([1.0, 0.0], [-1.0, 0.0]) - (-1.0)) < 1e-9


def test_cosine_zero_vector_is_zero_not_a_crash():
    assert _cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


if __name__ == "__main__":
    test_cosine_identical_vectors_is_one()
    test_cosine_orthogonal_vectors_is_zero()
    test_cosine_opposite_vectors_is_negative_one()
    test_cosine_zero_vector_is_zero_not_a_crash()
    print("all skill_normalize checks passed")
