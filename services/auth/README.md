# CareerLens Auth Service

Standalone microservice responsible for user authentication, registration, password hashing, and JWT token issuance. Extracted from the `/signup` and `/login` logic in the CareerLens monolith.

## Features

- **User Registration & Login**: Preserves the request/response shapes consumed by the frontend.
- **Argon2 Password Hashing**: State-of-the-art password hashing using `argon2-cffi` (no SHA-256).
- **JWT Token Issuance**: Signs HS256 tokens with `sub=<email>` and configurable expiration (`JWT_EXPIRE_MINUTES`).
- **Postgres Persistence**: SQLAlchemy 2.x with modern `psycopg` (v3) driver and automatic startup table migration via FastAPI `lifespan`.
- **Shared JWT Dependency**: Exposes `get_current_user_id` in `/services/common/jwt_auth.py` for other microservices to validate Bearer tokens.
- **Docker Ready**: Non-root container running `python:3.11-slim`.

---

## Endpoints

### 1. `GET /health`
Health check endpoint.
- **Response**: `{"status": "ok"}`

### 2. `POST /signup`
Registers a new user and returns an authentication token.
- **Request Body**:
  ```json
  {
    "full_name": "Alice Johnson",
    "email": "alice@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Success (200)**:
  ```json
  {
    "status": "success",
    "user_id": "alice@example.com",
    "access_token": "<JWT_TOKEN>",
    "token_type": "bearer"
  }
  ```
- **Error (400)**:
  ```json
  {
    "error": "Email already registered"
  }
  ```

### 3. `POST /login`
Authenticates a user by email and password and returns an authentication token.
- **Request Body**:
  ```json
  {
    "email": "alice@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Success (200)**:
  ```json
  {
    "status": "success",
    "user_id": "alice@example.com",
    "access_token": "<JWT_TOKEN>",
    "token_type": "bearer"
  }
  ```
- **Error (401)**:
  ```json
  {
    "error": "Invalid email or password"
  }
  ```

### 4. `GET /me`
Protected endpoint requiring `Authorization: Bearer <token>`. Returns current authenticated user.
- **Success (200)**:
  ```json
  {
    "status": "success",
    "user_id": "alice@example.com"
  }
  ```
- **Error (401)**:
  ```json
  {
    "error": "Token has expired",
    "detail": "Token has expired"
  }
  ```

---

## Database Schema

Table `users`:
| Column | Type | Constraints | Description |
|---|---|---|---|
| `email` | `VARCHAR` | Primary Key, Indexed | User email address |
| `full_name` | `VARCHAR` | Not Null | User full name |
| `password_hash` | `VARCHAR` | Not Null | Argon2 password hash string |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Not Null, Server Default `now()` | Record creation timestamp |

Tables are automatically verified and created at startup via FastAPI `lifespan`.

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | Postgres connection string (e.g., `postgresql+psycopg://user:pass@host:5432/dbname`) | *Required* |
| `JWT_SECRET` | Secret key used to sign HS256 JWT tokens (min 32 characters) | *Required* |
| `JWT_EXPIRE_MINUTES` | Token lifetime in minutes | `60` |
| `JWT_ALGORITHM` | JWT cryptographic algorithm | `HS256` |

---

## Local Development Setup

### 1. Start Local Postgres Container
Run an official PostgreSQL container using Docker:

```bash
docker run -d \
  --name careerlens-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=careerlens_auth \
  -p 5432:5432 \
  postgres:15
```

> **Note**: If port `5432` is already allocated on your machine, you can map it to `5433`:
> `-p 5433:5432` and update `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/careerlens_auth`.

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r services/auth/requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` (or set environment variables):
```bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/careerlens_auth
export JWT_SECRET=supersecretjwtkeyforcareerlensauthservice123456
export JWT_EXPIRE_MINUTES=60
```

### 5. Run Service
```bash
cd services/auth
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Running with Docker

### Build Docker Image
```bash
docker build -t careerlens-auth ./services/auth
```

### Run Container
```bash
docker run -d \
  --name careerlens-auth \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/careerlens_auth \
  -e JWT_SECRET=supersecretjwtkeyforcareerlensauthservice123456 \
  -e JWT_EXPIRE_MINUTES=60 \
  careerlens-auth
```

---

## Running Tests

Execute the automated pytest suite against the running Postgres database:

```bash
# Run from repository root
pytest -v services/auth/tests

# Or run from inside services/auth
cd services/auth
pytest -v tests
```

### Running Tests Inside Docker Container
```bash
docker run --rm \
  -e DATABASE_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/careerlens_auth \
  -e JWT_SECRET=supersecretjwtkeyforcareerlensauthservice123456 \
  careerlens-auth pytest -v tests
```

---

## Example cURL Commands

### Health Check
```bash
curl -X GET http://localhost:8000/health
```

### Signup
```bash
curl -X POST http://localhost:8000/signup \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Test User", "email": "test@example.com", "password": "Password123!"}'
```

### Login
```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Password123!"}'
```

### Access Protected Endpoint
```bash
curl -X GET http://localhost:8000/me \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```
