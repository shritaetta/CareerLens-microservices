#!/usr/bin/env python3
"""
CareerLens End-to-End Verification Script:
Verifies Auth -> Profile workflow:
1. Signs up a new user via the Auth service.
2. Extracts the Bearer JWT token.
3. Saves a user profile via the Profile service.
4. Reads the saved profile back and verifies integrity.
5. Verifies 403 Forbidden protection against other users' profiles.
6. Verifies 401 Unauthorized protection when no token is supplied.
"""

import os
import sys
import uuid
from pathlib import Path

# Setup paths
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "services" / "auth"))
sys.path.insert(0, str(repo_root / "services" / "profile"))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5433/careerlens_auth",
)
os.environ.setdefault(
    "JWT_SECRET",
    "test_super_secret_jwt_key_that_is_at_least_32_bytes_long_careerlens",
)
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")


def run_e2e_verification():
    import httpx
    from fastapi.testclient import TestClient

    auth_url = os.getenv("AUTH_SERVICE_URL")
    profile_url = os.getenv("PROFILE_SERVICE_URL")

    unique_suffix = uuid.uuid4().hex[:8]
    test_email = f"e2e_{unique_suffix}@careerlens.local"
    test_password = f"P@ssword_{unique_suffix}!"
    test_name = f"Student {unique_suffix}"

    print("==================================================")
    print("CareerLens End-to-End Auth -> Profile Verification")
    print("==================================================")

    if auth_url and profile_url:
        print(f"Running against LIVE endpoints:")
        print(f"  Auth Service:    {auth_url}")
        print(f"  Profile Service: {profile_url}\n")
        auth_client = httpx.Client(base_url=auth_url)
        profile_client = httpx.Client(base_url=profile_url)
    else:
        print("Running against in-process FastAPI service instances...\n")
        from services.auth.main import app as auth_app
        from services.profile.main import app as profile_app

        auth_client = TestClient(auth_app)
        profile_client = TestClient(profile_app)

    # 1. Signup via Auth Service
    print(f"[1/6] Registering user '{test_email}' via Auth service...")
    signup_resp = auth_client.post(
        "/signup",
        json={
            "full_name": test_name,
            "email": test_email,
            "password": test_password,
        },
    )
    if signup_resp.status_code != 200:
        print(f"FAILED: Signup returned {signup_resp.status_code}: {signup_resp.text}")
        sys.exit(1)

    signup_data = signup_resp.json()
    token = signup_data.get("access_token")
    user_id = signup_data.get("user_id")

    assert token, "Token not found in signup response"
    assert user_id == test_email, f"Expected user_id {test_email}, got {user_id}"
    print(f"      OK - User registered. Token received (len={len(token)}).")

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check profile before saving (should return 'Profile not found')
    print(f"[2/6] Checking initial profile state via Profile service...")
    initial_get = profile_client.get(f"/profile/{test_email}", headers=headers)
    assert initial_get.status_code == 200
    assert initial_get.json() == {"error": "Profile not found"}
    print("      OK - Profile not found as expected.")

    # 3. Save profile via Profile Service
    profile_data = {
        "fullName": test_name,
        "email": test_email,
        "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Machine Learning"],
        "education": {
            "graduation": {
                "institute": "Stanford University",
                "degree": "B.S. Symbolic Systems",
                "year": 2026,
            }
        },
        "achievements": "Built autonomous coding agents",
        "preferredDomains": ["AI Engineering", "Systems"],
    }
    print(f"[3/6] Saving profile data via Profile service with Bearer token...")
    save_resp = profile_client.post(
        f"/profile/{test_email}",
        json=profile_data,
        headers=headers,
    )
    if save_resp.status_code != 200:
        print(f"FAILED: Save profile returned {save_resp.status_code}: {save_resp.text}")
        sys.exit(1)
    assert save_resp.json() == {"status": "success"}
    print("      OK - Profile successfully saved.")

    # 4. Read profile back
    print(f"[4/6] Retrieving profile from Profile service...")
    get_resp = profile_client.get(f"/profile/{test_email}", headers=headers)
    if get_resp.status_code != 200:
        print(f"FAILED: Get profile returned {get_resp.status_code}: {get_resp.text}")
        sys.exit(1)
    retrieved = get_resp.json()
    assert retrieved["user_id"] == test_email
    assert retrieved["profile_data"] == profile_data
    print("      OK - Retrieved profile matches saved data exactly.")

    # 5. Test 403 Forbidden Isolation
    print(f"[5/6] Verifying user isolation (attempting cross-user access)...")
    other_email = f"other_{uuid.uuid4().hex[:6]}@careerlens.local"
    forbidden_get = profile_client.get(f"/profile/{other_email}", headers=headers)
    assert forbidden_get.status_code == 403, f"Expected 403, got {forbidden_get.status_code}"
    assert "forbidden" in forbidden_get.json().get("error", "").lower()

    forbidden_post = profile_client.post(
        f"/profile/{other_email}",
        json={"skills": ["Unauthorized"]},
        headers=headers,
    )
    assert forbidden_post.status_code == 403, f"Expected 403, got {forbidden_post.status_code}"
    print("      OK - Cross-user profile access correctly blocked with 403 Forbidden.")

    # 6. Test 401 Unauthorized
    print(f"[6/6] Verifying token requirement (missing token access)...")
    unauth_resp = profile_client.get(f"/profile/{test_email}")
    assert unauth_resp.status_code == 401, f"Expected 401, got {unauth_resp.status_code}"
    print("      OK - Access without token correctly blocked with 401 Unauthorized.")

    print("\n==================================================")
    print("ALL END-TO-END VERIFICATIONS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    run_e2e_verification()
