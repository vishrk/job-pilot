from app.services.answer_library import normalize_question


def test_normalize_collapses_punctuation_and_case():
    assert normalize_question("Years of Python?") == normalize_question("years of python")


def test_normalize_treats_rephrasing_as_distinct():
    # deliberately conservative: only exact-normalized matches hit the cache,
    # a genuinely different phrasing gets its own LLM-drafted answer
    assert normalize_question("Years of Python experience?") != normalize_question("Python experience, how many years?")


if __name__ == "__main__":
    test_normalize_collapses_punctuation_and_case()
    test_normalize_treats_rephrasing_as_distinct()
    print("all answer_library checks passed")
