from app.models import Hunt
from app.services.hunt_runner import _matches_filters


def _hunt(roles=None, locations=None):
    return Hunt(roles=roles or [], locations=locations or [])


def test_no_filters_matches_everything():
    assert _matches_filters("Software Engineer", "Remote", _hunt())


def test_role_filter_matches_substring_case_insensitive():
    hunt = _hunt(roles=["software engineer"])
    assert _matches_filters("Senior Software Engineer, Platform", "Remote", hunt)
    assert not _matches_filters("Product Manager", "Remote", hunt)


def test_location_filter_matches_substring():
    hunt = _hunt(locations=["San Francisco"])
    assert _matches_filters("Software Engineer", "San Francisco, CA", hunt)
    assert not _matches_filters("Software Engineer", "New York, NY", hunt)


def test_location_filter_ignored_when_job_location_missing():
    hunt = _hunt(locations=["San Francisco"])
    assert _matches_filters("Software Engineer", None, hunt)


if __name__ == "__main__":
    test_no_filters_matches_everything()
    test_role_filter_matches_substring_case_insensitive()
    test_location_filter_matches_substring()
    test_location_filter_ignored_when_job_location_missing()
    print("all hunt_runner checks passed")
