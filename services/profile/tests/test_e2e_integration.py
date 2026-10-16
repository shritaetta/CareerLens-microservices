import uuid
import pytest
from fastapi.testclient import TestClient

try:
    from services.auth.main import app as auth_app
except ImportError:
    auth_app = None

try:
    from main import app as profile_app
except ImportError:
    from services.profile.main import app as profile_app

pytestmark = pytest.mark.skipif(
    auth_app is None,
    reason="Auth service not available in isolated profile container",
)


def test_auth_to_profile_end_to_end():
    """End-to-end integration: signup via Auth service, save and read profile via Profile service."""
    with TestClient(auth_app) as auth_client, TestClient(profile_app) as profile_client:
        unique_id = uuid.uuid4().hex[:8]
        user_email = f"e2e_{unique_id}@example.com"
        user_password = "E2E_SecurePassword!99"

        # Step 1: Sign up a new user via Auth service
        signup_payload = {
            "full_name": f"E2E Student {unique_id}",
            "email": user_email,
            "password": user_password,
        }
        signup_res = auth_client.post("/signup", json=signup_payload)
        assert signup_res.status_code == 200, f"Signup failed: {signup_res.text}"
        signup_data = signup_res.json()

        assert signup_data["status"] == "success"
        assert signup_data["user_id"] == user_email
        assert signup_data["token_type"] == "bearer"
        access_token = signup_data["access_token"]
        assert access_token, "No access token returned from signup"

        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 2: Read profile before saving (should return 'Profile not found')
        initial_get = profile_client.get(f"/profile/{user_email}", headers=headers)
        assert initial_get.status_code == 200
        assert initial_get.json() == {"error": "Profile not found"}

        # Step 3: Save user profile via Profile service using the Auth JWT
        profile_content = {
            "fullName": f"E2E Student {unique_id}",
            "email": user_email,
            "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
            "education": {
                "graduation": {
                    "institute": "Tech Institute",
                    "degree": "B.S. in Computer Science",
                    "cgpa": "3.9",
                }
            },
            "achievements": "Built full-stack microservices platform",
            "preferredDomains": ["Backend Development", "Cloud Systems"],
            "drafts": [
                {
                    "id": f"draft-e2e-{unique_id}",
                    "title": "Backend Engineering Resume",
                    "updatedAt": "2026-10-16",
                }
            ],
            "likedInternships": ["intern-backend-001", "intern-cloud-002"],
        }
        save_res = profile_client.post(
            f"/profile/{user_email}",
            json=profile_content,
            headers=headers,
        )
        assert save_res.status_code == 200, f"Save profile failed: {save_res.text}"
        assert save_res.json() == {"status": "success"}

        # Step 4: Retrieve saved profile and verify exact data
        get_res = profile_client.get(f"/profile/{user_email}", headers=headers)
        assert get_res.status_code == 200, f"Get profile failed: {get_res.text}"
        get_data = get_res.json()

        assert get_data["user_id"] == user_email
        assert get_data["profile_data"] == profile_content

        # Step 5: Verify cross-user isolation (403 Forbidden when accessing another user's profile)
        other_user = f"victim_{unique_id}@example.com"
        forbidden_get = profile_client.get(f"/profile/{other_user}", headers=headers)
        assert forbidden_get.status_code == 403
        assert "forbidden" in forbidden_get.json()["error"].lower()

        forbidden_post = profile_client.post(
            f"/profile/{other_user}",
            json={"skills": ["Malicious Overwrite"]},
            headers=headers,
        )
        assert forbidden_post.status_code == 403
        assert "forbidden" in forbidden_post.json()["error"].lower()

        # Step 6: Verify missing token returns 401 Unauthorized
        unauthorized_res = profile_client.get(f"/profile/{user_email}")
        assert unauthorized_res.status_code == 401
        assert "error" in unauthorized_res.json()
