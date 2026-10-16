from datetime import timedelta
from fastapi import HTTPException
import pytest
from common.jwt_auth import create_access_token


def test_health_ready(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_not_ready():
    import main
    from data_loader import InternshipDataLoader

    unloaded_loader = InternshipDataLoader()
    original_loader = main.loader
    try:
        main.loader = unloaded_loader
        with pytest.raises(HTTPException) as exc_info:
            main.health()
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["status"] == "not ready"
    finally:
        main.loader = original_loader


def test_auth_enforcement_missing_token(client):
    assert client.get("/internships/light").status_code == 401
    assert (
        client.post(
            "/evaluate_ats",
            json={"resume_text": "", "internship_id": "1", "user_skills": []},
        ).status_code
        == 401
    )
    assert client.post("/enhance_profile", json={}).status_code == 401
    assert (
        client.post(
            "/feedback", json={"internship_id": "1", "reason": "not_my_domain"}
        ).status_code
        == 401
    )
    assert client.post("/recommend", json={"skills": ["Python"]}).status_code == 401


def test_auth_enforcement_invalid_token(client):
    headers = {"Authorization": "Bearer invalid.token.value"}
    assert client.get("/internships/light", headers=headers).status_code == 401
    assert (
        client.post("/recommend", headers=headers, json={"skills": ["Python"]}).status_code
        == 401
    )


def test_auth_enforcement_expired_token(client):
    expired_token = create_access_token("test_user", expires_delta=timedelta(seconds=-10))
    headers = {"Authorization": f"Bearer {expired_token}"}
    resp = client.get("/internships/light", headers=headers)
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_internships_light_endpoint(client, token_factory):
    token = token_factory("test_user_light")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/internships/light", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "id" in first
    assert "title" in first


def test_evaluate_ats_endpoint(client, token_factory):
    token = token_factory("test_user_ats")
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch light list first to grab a valid ID
    light_resp = client.get("/internships/light", headers=headers)
    assert light_resp.status_code == 200
    first_id = light_resp.json()[0]["id"]

    resp = client.post(
        "/evaluate_ats",
        headers=headers,
        json={
            "resume_text": "Experienced Python web developer with FastAPI and SQL experience.",
            "internship_id": str(first_id),
            "user_skills": ["Python", "FastAPI"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "score" in data
    assert "matched_skills" in data
    assert 0 <= data["score"] <= 100


def test_enhance_profile_endpoint(client, token_factory):
    token = token_factory("test_user_enhance")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "fullName": "Alice Smith",
        "skills": ["python", "docker", "leadership"],
        "projects": [
            {
                "title": "E-Commerce",
                "description": "worked on the backend microservices using FastAPI",
                "tech": "FastAPI, Docker / PostgreSQL",
            }
        ],
        "experience": [],
        "achievements": ["Won 1st place in national hackathon"],
        "certificates": [
            {
                "extracted_text": "has successfully completed the online course Machine Learning With Python",
                "filename": "ml_cert.pdf",
            }
        ],
    }
    resp = client.post("/enhance_profile", headers=headers, json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "success"
    enhanced = res["enhanced_profile"]
    assert "skills" in enhanced
    assert isinstance(enhanced["skills"], list)
    assert "projects" in enhanced
    assert "Developed and implemented" in enhanced["projects"][0]["description"]
    assert enhanced["certificates"] == ["Machine Learning With Python"]
