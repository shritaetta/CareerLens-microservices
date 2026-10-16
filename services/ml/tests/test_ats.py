import pytest


def test_evaluate_ats_valid_fixture(shared_loader):
    # Choose first internship from loader as fixture
    fixture_internship = shared_loader.get_all()[0]
    internship_id = str(fixture_internship.get("id", 0))

    resume_text = (
        "Experienced Python software engineer skilled in FastAPI, SQL databases, "
        "machine learning algorithms, Docker containerization, and RESTful APIs."
    )
    user_skills = ["Python", "FastAPI", "SQL", "Docker"]

    result = shared_loader.evaluate_ats(
        resume_text=resume_text,
        internship_id=internship_id,
        user_skills=user_skills,
    )

    assert "score" in result
    assert isinstance(result["score"], int)
    assert 0 <= result["score"] <= 100

    assert "matched_skills" in result
    assert isinstance(result["matched_skills"], list)

    assert "missing_skills" in result
    assert isinstance(result["missing_skills"], list)

    assert "suggestions" in result
    assert isinstance(result["suggestions"], list)

    assert "semantic_score" in result
    assert isinstance(result["semantic_score"], float)
    assert 0.0 <= result["semantic_score"] <= 1.0


def test_evaluate_ats_not_found(shared_loader):
    result = shared_loader.evaluate_ats(
        resume_text="Some resume text",
        internship_id="non_existent_internship_id_999999",
        user_skills=["Python"],
    )
    assert result == {"error": "Internship not found"}


def test_evaluate_ats_keyword_extraction(shared_loader):
    fixture = shared_loader.get_all()[0]
    internship_id = str(fixture.get("id", 0))

    # Test with empty explicit user_skills, but keywords mentioned in resume text
    resume_with_text = "Experienced in python and engineering principles."
    result = shared_loader.evaluate_ats(
        resume_text=resume_with_text,
        internship_id=internship_id,
        user_skills=[],
    )
    assert "score" in result
    assert 0 <= result["score"] <= 100
