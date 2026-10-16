from datetime import timedelta
from sqlalchemy import text
from database import get_engine
from common.jwt_auth import create_access_token, decode_access_token


def test_health(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_signup(client):
    """Test successful user registration with Argon2 password hashing."""
    payload = {
        "full_name": "Alice Johnson",
        "email": "alice@example.com",
        "password": "Password123!",
    }
    response = client.post("/signup", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["user_id"] == "alice@example.com"
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert isinstance(data["access_token"], str) and len(data["access_token"]) > 20

    # Verify token payload
    decoded = decode_access_token(data["access_token"])
    assert decoded["sub"] == "alice@example.com"

    # Verify password in database is Argon2 hashed, not plaintext or SHA256
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT email, full_name, password_hash FROM users WHERE email = :email"),
            {"email": "alice@example.com"},
        ).fetchone()

        assert row is not None
        assert row[0] == "alice@example.com"
        assert row[1] == "Alice Johnson"
        assert row[2] != "Password123!"
        assert row[2].startswith("$argon2")


def test_duplicate_signup(client):
    """Test registering an existing email returns error with 400 status."""
    payload = {
        "full_name": "Bob Smith",
        "email": "bob@example.com",
        "password": "SecretPassword123",
    }
    # First registration
    res1 = client.post("/signup", json=payload)
    assert res1.status_code == 200

    # Duplicate registration
    res2 = client.post("/signup", json=payload)
    assert res2.status_code == 400
    data = res2.json()
    assert "error" in data
    assert data["error"] == "Email already registered"


def test_login_ok(client):
    """Test successful user login returning valid token and user_id."""
    signup_payload = {
        "full_name": "Charlie Brown",
        "email": "charlie@example.com",
        "password": "MySuperSecretPassword",
    }
    client.post("/signup", json=signup_payload)

    login_payload = {
        "email": "charlie@example.com",
        "password": "MySuperSecretPassword",
    }
    response = client.post("/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["user_id"] == "charlie@example.com"
    assert data["token_type"] == "bearer"
    assert "access_token" in data

    # Verify token decoded sub matches user email
    decoded = decode_access_token(data["access_token"])
    assert decoded["sub"] == "charlie@example.com"


def test_login_wrong_password(client):
    """Test login with incorrect password returns 401 and error shape."""
    signup_payload = {
        "full_name": "Dana Scully",
        "email": "dana@example.com",
        "password": "TheTruthIsOutThere",
    }
    client.post("/signup", json=signup_payload)

    login_payload = {
        "email": "dana@example.com",
        "password": "WrongPassword456",
    }
    response = client.post("/login", json=login_payload)
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"] == "Invalid email or password"


def test_login_nonexistent_user(client):
    """Test login with an email that does not exist."""
    login_payload = {
        "email": "unknown_user@example.com",
        "password": "SomePassword",
    }
    response = client.post("/login", json=login_payload)
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"] == "Invalid email or password"


def test_token_validation(client):
    """Test that a valid JWT token authorizes access to protected endpoints."""
    signup_payload = {
        "full_name": "Fox Mulder",
        "email": "mulder@example.com",
        "password": "IWantToBelieve123",
    }
    signup_res = client.post("/signup", json=signup_payload)
    token = signup_res.json()["access_token"]

    # Access protected /me endpoint with valid token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["status"] == "success"
    assert me_data["user_id"] == "mulder@example.com"


def test_expired_token(client):
    """Test that an expired JWT token is rejected with 401."""
    # Create token expired 10 minutes ago
    expired_token = create_access_token(
        "expired_user@example.com",
        expires_delta=timedelta(minutes=-10),
    )

    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/me", headers=headers)
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert "expired" in data["error"].lower()


def test_invalid_token(client):
    """Test that a malformed or corrupted token is rejected with 401."""
    headers = {"Authorization": "Bearer not.a.valid.jwt.token"}
    response = client.get("/me", headers=headers)
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert "invalid" in data["error"].lower()


def test_missing_token(client):
    """Test that accessing protected endpoint without token returns 401."""
    response = client.get("/me")
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert "missing" in data["error"].lower() or "invalid" in data["error"].lower()
