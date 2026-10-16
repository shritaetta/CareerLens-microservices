# CareerLens Profile Service

Standalone microservice responsible for user profile persistence, retrieval, and updates. Extracted from `/backend/database.py` and the matching routes in `/backend/main.py`.

## Features

- **Profile Persistence**: Stores full user profiles in PostgreSQL using `JSONB` for schema flexibility (supporting skills, education, achievements, resume drafts, liked internships, and arbitrary domain data).
- **Strict Authorization**: Both `GET /profile/{user_id}` and `POST /profile/{user_id}` require a valid Bearer JWT. The `user_id` parameter in the route must match the token's `sub` claim; any mismatch triggers an immediate HTTP `403 Forbidden` response, closing the vulnerability in the monolith where any caller could access arbitrary profiles.
- **FastAPI Lifespan**: Automatic table creation on startup via modern FastAPI `lifespan`.
- **Docker Ready**: Non-root container running `python:3.11-slim`.

---

## Endpoints

### 1. `GET /health`
Health check endpoint.
- **Response**: `{"status": "ok"}`

### 2. `GET /profile/{user_id}`
Retrieves saved profile data for the authenticated user.
- **Headers**: `Authorization: Bearer <JWT_TOKEN>`
- **Authorization**: Token `sub` must match `{user_id}`, otherwise returns `403 Forbidden`.
- **Success (200)**:
  ```json
  {
    "user_id": "alice@example.com",
    "profile_data": {
      "fullName": "Alice Johnson",
      "email": "alice@example.com",
      "skills": ["Python", "FastAPI", "React", "PostgreSQL"],
      "education": {
        "graduation": {
          "institute": "Tech University",
          "degree": "B.Tech Computer Science",
          "year": 2025
        }
      },
      "achievements": "First place in National Hackathon 2024",
      "preferredDomains": ["Software Development", "Machine Learning"]
    }
  }
  ```
- **Not Found (200)**:
  ```json
  {
    "error": "Profile not found"
  }
  ```
- **Unauthorized (401)**: Missing or invalid token.
- **Forbidden (403)**: Token `sub` does not match URL `{user_id}`.

### 3. `POST /profile/{user_id}`
Saves or updates profile data for the authenticated user. Accepts arbitrary JSON object body.
- **Headers**:
  - `Content-Type: application/json`
  - `Authorization: Bearer <JWT_TOKEN>`
- **Authorization**: Token `sub` must match `{user_id}`, otherwise returns `403 Forbidden`.
- **Request Body**: Arbitrary JSON dictionary, for example:
  ```json
  {
    "fullName": "Alice Johnson",
    "skills": ["Python", "FastAPI", "React"],
    "education": {
      "graduation": { "institute": "Tech University" }
    }
  }
  ```
- **Success (200)**:
  ```json
  {
    "status": "success"
  }
  ```
- **Unauthorized (401)**: Missing or invalid token.
- **Forbidden (403)**: Token `sub` does not match URL `{user_id}`.

---

## Database Schema

Table `profiles`:
| Column | Type | Constraints | Description |
|---|---|---|---|
| `user_id` | `TEXT` | Primary Key | User email identifier matching JWT `sub` |
| `profile_data` | `JSONB` | Not Null | Structured profile document |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Not Null, Server Default `now()` | Last modification timestamp |

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | Postgres connection string (e.g., `postgresql+psycopg://user:pass@host:5432/careerlens_auth`) | *Required* |
| `JWT_SECRET` | Secret key used to validate HS256 Bearer tokens | *Required* |
| `JWT_ALGORITHM` | JWT cryptographic algorithm | `HS256` |
| `JWT_EXPIRE_MINUTES` | Expected token validity window | `60` |

---

## Local Development Setup

### 1. Start Local Postgres Container
```bash
docker run -d \
  --name careerlens-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=careerlens_auth \
  -p 5432:5432 \
  postgres:15
```

### 2. Install Dependencies
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install -r services/profile/requirements.txt
```

### 3. Run the Service
```bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/careerlens_auth
export JWT_SECRET=supersecretjwtkeyforcareerlensauthservice123456

cd services/profile
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

---

## Running with Docker

### Build Docker Image
```bash
docker build -t careerlens-profile ./services/profile
```

### Run Container
```bash
docker run -d \
  --name careerlens-profile \
  -p 8002:8000 \
  -e DATABASE_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/careerlens_auth \
  -e JWT_SECRET=supersecretjwtkeyforcareerlensauthservice123456 \
  careerlens-profile
```

---

## Running Tests

### Pytest Unit & Integration Tests
```bash
pytest -v services/profile/tests
```

### End-to-End Verification Script
Run the standalone verification script that signs up via the Auth service, obtains a JWT token, saves a profile, reads it back, and tests 403/401 enforcement:
```bash
python services/profile/verify_e2e.py
```

### Running Tests in Docker
```bash
docker run --rm \
  -e DATABASE_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/careerlens_auth \
  -e JWT_SECRET=supersecretjwtkeyforcareerlensauthservice123456 \
  careerlens-profile pytest -v tests
```
