import pytest


def test_recommendations_exclude_ids(shared_loader):
    # 1. Get baseline top 3
    baseline = shared_loader.get_recommendations("Python data science machine learning", top_n=3)
    assert len(baseline) == 3
    first_id = baseline[0]["id"]

    # 2. Add constraint to exclude first_id
    constraints = {"exclude_ids": [str(first_id)]}
    filtered = shared_loader.get_recommendations(
        "Python data science machine learning", top_n=3, constraints=constraints
    )

    returned_ids = [r["id"] for r in filtered]
    assert first_id not in returned_ids
    assert len(filtered) == 3


def test_recommendations_exclude_location(shared_loader):
    # Get all internships to inspect existing locations
    all_internships = shared_loader.get_all()
    sample_loc = next(i["location"] for i in all_internships if i.get("location"))

    constraints = {"exclude_locations": [sample_loc]}
    filtered = shared_loader.get_recommendations(
        "software engineering web development", top_n=10, constraints=constraints
    )

    for item in filtered:
        assert item.get("location") != sample_loc


def test_recommendations_exclude_domain(shared_loader):
    all_internships = shared_loader.get_all()
    sample_domain = next(i["domain"] for i in all_internships if i.get("domain"))

    constraints = {"exclude_domains": [sample_domain]}
    filtered = shared_loader.get_recommendations(
        "internship opportunities", top_n=10, constraints=constraints
    )

    for item in filtered:
        assert item.get("domain") != sample_domain


def test_recommendations_exclude_duration(shared_loader):
    all_internships = shared_loader.get_all()
    sample_duration = next(i["duration"] for i in all_internships if i.get("duration"))

    constraints = {"exclude_durations": [sample_duration]}
    filtered = shared_loader.get_recommendations(
        "full stack developer", top_n=10, constraints=constraints
    )

    for item in filtered:
        assert item.get("duration") != sample_duration


def test_recommendations_min_stipend_filter(shared_loader):
    from data_loader import parse_numeric_stipend

    min_stipend = 10000
    constraints = {"min_stipend": min_stipend}
    filtered = shared_loader.get_recommendations(
        "software engineer python", top_n=10, constraints=constraints
    )

    for item in filtered:
        stipend_val = parse_numeric_stipend(item.get("stipend", "0"))
        assert stipend_val > min_stipend


def test_recommendations_clean_response_shape(shared_loader):
    recs = shared_loader.get_recommendations("Python developer", top_n=3)
    assert len(recs) <= 3
    for r in recs:
        assert "_numeric_stipend" not in r
        assert "match_score" in r
        assert isinstance(r["match_score"], float)
