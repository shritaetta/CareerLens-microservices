def test_health(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_profile_not_found(client, create_token):
    """Test GET profile when no profile exists returns error shape."""
    user_id = "newuser@example.com"
    token = create_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/profile/{user_id}", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"error": "Profile not found"}


def test_save_and_get_profile(client, create_token):
    """Test saving a new profile and retrieving it with matching payload."""
    user_id = "alice@example.com"
    token = create_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}

    profile_payload = {
        "fullName": "Alice Johnson",
        "email": user_id,
        "skills": ["Python", "FastAPI", "React", "PostgreSQL"],
        "education": {
            "graduation": {
                "institute": "Tech University",
                "degree": "B.Tech Computer Science",
                "year": 2025,
            }
        },
        "achievements": "First place in National Hackathon 2024",
        "preferredDomains": ["Software Development", "Machine Learning"],
    }

    # 1. Save profile
    save_res = client.post(f"/profile/{user_id}", json=profile_payload, headers=headers)
    assert save_res.status_code == 200
    assert save_res.json() == {"status": "success"}

    # 2. Get profile
    get_res = client.get(f"/profile/{user_id}", headers=headers)
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["user_id"] == user_id
    assert data["profile_data"] == profile_payload


def test_update_profile(client, create_token):
    """Test updating an existing profile replaces previous data."""
    user_id = "bob@example.com"
    token = create_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}

    initial_payload = {
        "skills": ["JavaScript", "HTML"],
        "summary": "Junior developer",
    }
    updated_payload = {
        "skills": ["JavaScript", "TypeScript", "React", "Node.js"],
        "summary": "Full Stack developer",
        "drafts": [{"id": "draft-1", "title": "Software Engineer Resume"}],
        "likedInternships": ["internship-101", "internship-202"],
    }

    # Initial save
    res1 = client.post(f"/profile/{user_id}", json=initial_payload, headers=headers)
    assert res1.status_code == 200

    # Update save
    res2 = client.post(f"/profile/{user_id}", json=updated_payload, headers=headers)
    assert res2.status_code == 200

    # Fetch updated
    get_res = client.get(f"/profile/{user_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["profile_data"] == updated_payload


def test_401_without_token(client):
    """Test accessing or saving profile without a token returns 401."""
    user_id = "anyone@example.com"

    # GET without token
    get_res = client.get(f"/profile/{user_id}")
    assert get_res.status_code == 401
    assert "error" in get_res.json()

    # POST without token
    post_res = client.post(f"/profile/{user_id}", json={"skills": ["Python"]})
    assert post_res.status_code == 401
    assert "error" in post_res.json()


def test_401_with_invalid_token(client):
    """Test accessing profile with invalid token returns 401."""
    headers = {"Authorization": "Bearer malformed.invalid.token"}
    response = client.get("/profile/user@example.com", headers=headers)
    assert response.status_code == 401
    assert "error" in response.json()


def test_403_for_another_users_id_get(client, create_token):
    """Test GET /profile/{user_id} with another user's token returns 403."""
    user_token = create_token("user_a@example.com")
    headers = {"Authorization": f"Bearer {user_token}"}

    # Attempt to read user_b's profile with user_a's token
    response = client.get("/profile/user_b@example.com", headers=headers)
    assert response.status_code == 403
    data = response.json()
    assert "error" in data
    assert "forbidden" in data["error"].lower()


def test_403_for_another_users_id_post(client, create_token):
    """Test POST /profile/{user_id} with another user's token returns 403."""
    user_token = create_token("user_a@example.com")
    headers = {"Authorization": f"Bearer {user_token}"}

    # Attempt to overwrite user_b's profile with user_a's token
    response = client.post(
        "/profile/user_b@example.com",
        json={"skills": ["Hacked Skills"]},
        headers=headers,
    )
    assert response.status_code == 403
    data = response.json()
    assert "error" in data
    assert "forbidden" in data["error"].lower()
