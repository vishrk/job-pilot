from app.services.job_dedup import normalize_title


def test_normalize_title_collapses_punctuation_and_case():
    assert normalize_title("Senior Software Engineer, Platform") == normalize_title(
        "senior software engineer platform"
    )


def test_normalize_title_collapses_whitespace():
    assert normalize_title("Staff  Engineer   (Remote)") == normalize_title("Staff Engineer Remote")


def test_normalize_title_distinguishes_different_roles():
    assert normalize_title("Software Engineer") != normalize_title("Senior Software Engineer")


if __name__ == "__main__":
    test_normalize_title_collapses_punctuation_and_case()
    test_normalize_title_collapses_whitespace()
    test_normalize_title_distinguishes_different_roles()
    print("all job_dedup checks passed")
