# CareerLens ML Recommendation & Enhancement Service

The ML service (`services/ml`) handles semantic search, candidate recommendations, ATS resume scoring, resume enhancement, and Redis-backed active learning feedback loops for the CareerLens platform.

---

## Features

- **Semantic Recommendations (`POST /recommend`)**: Uses `all-MiniLM-L6-v2` SentenceTransformer embeddings and cosine similarity against indexed internships.
- **Persistent Feedback Loop (`POST /feedback`)**: Binds feedback to the authenticated user's JWT `sub` and stores constraints in Redis under key `feedback:{user_id}`. Restarts and replica instances persistently exclude disliked opportunities.
- **ATS Evaluation (`POST /evaluate_ats`)**: Computes hybrid semantic + keyword matching ATS scores (0–100) with tailored suggestions.
- **Profile Enhancement (`POST /enhance_profile`)**: Categorizes skills using rule-based and semantic classification, improves action verbs, cleans certificate course names, and formats professional summaries.
- **Dropdown Metadata (`GET /internships/light`)**: Returns minimal `{id, title}` pairs for UI selectors.
- **Embedding Cache**: Caches precomputed dataset embeddings to a `.npy` file next to the dataset (keyed by the file's `mtime` and content SHA-256 hash) to make restarts and replicas instantaneous.
- **Security**: JWT Bearer token authentication on all endpoints except `/health`.

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATASET_PATH` | Path to the Excel dataset file (`.xlsx`) | `data/Book2.xlsx` |
| `REDIS_URL` | Redis connection URL for user feedback storage | `redis://localhost:6379/0` |
| `JWT_SECRET` | Secret key used to sign and verify Bearer JWT tokens | *(Required in production)* |
| `JWT_ALGORITHM` | Algorithm used for JWT encoding/decoding | `HS256` |
| `JWT_EXPIRE_MINUTES` | Access token lifespan in minutes | `60` |

---

## Running Locally

### Prerequisites

- Python 3.11+
- Redis (running locally on port 6379 or via Docker)

### 1. Install Dependencies

```bash
pip install -r services/ml/requirements.txt
```

### 2. Configure Environment

Copy `.env.example`:

```bash
cp services/ml/.env.example services/ml/.env
```

Ensure `JWT_SECRET` and `DATASET_PATH` are set appropriately.

### 3. Start the Service

From the repository root:

```bash
uvicorn services.ml.main:app --host 0.0.0.0 --port 8000 --reload
```

Or from inside `services/ml`:

```bash
cd services/ml
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Running with Docker

### 1. Build the Docker Image

The Dockerfile builds on `python:3.11-slim`, downloads model weights at build time into `/home/appuser/.cache`, and executes as a non-root user (`appuser` with UID 1000):

```bash
docker build -t careerlens-ml ./services/ml
```

### 2. Run the Container

Run the container with the dataset directory mounted and connected to Redis:

```bash
docker run -d \
  --name careerlens-ml \
  -p 8003:8000 \
  -e DATASET_PATH=/app/data/Book2.xlsx \
  -e REDIS_URL=redis://host.docker.internal:6379/0 \
  -e JWT_SECRET=your_super_secret_jwt_key_here \
  -v $(pwd)/data:/app/data \
  careerlens-ml
```

---

## API Endpoints

### 1. `GET /health`
- **Auth**: None
- **Response**: `200 OK` `{"status": "ok"}` only once model, dataset, and embeddings are loaded (returns `503 Service Unavailable` if loading).

### 2. `GET /internships/light`
- **Auth**: Bearer JWT
- **Response**:
```json
[
  {"id": "1", "title": "Machine Learning Intern"},
  {"id": "2", "title": "Frontend Engineer Intern"}
]
```

### 3. `POST /recommend`
- **Auth**: Bearer JWT (binds to token's `sub`, ignoring any `user_id` in body)
- **Request Body**:
```json
{
  "skills": ["Python", "FastAPI", "Machine Learning"],
  "education": "B.Tech Computer Science",
  "achievements": "Hackathon Winner",
  "resume_text": "Experienced Python software engineer...",
  "certificate_text": ""
}
```
- **Response**: Top 3 matching internships with `match_score`, filtered against Redis feedback constraints.

### 4. `POST /feedback`
- **Auth**: Bearer JWT (binds to token's `sub`)
- **Request Body**:
```json
{
  "internship_id": "1",
  "reason": "location_not_suitable",
  "metadata": {"location": "Remote"}
}
```
- **Response**:
```json
{
  "status": "success",
  "constraints_updated": true,
  "active_constraints": {
    "exclude_locations": ["Remote"],
    "min_stipend": -1,
    "exclude_domains": [],
    "exclude_durations": [],
    "exclude_ids": ["1"]
  }
}
```

### 5. `POST /evaluate_ats`
- **Auth**: Bearer JWT
- **Request Body**:
```json
{
  "resume_text": "Experienced Python developer with PyTorch...",
  "internship_id": "1",
  "user_skills": ["Python", "Docker"]
}
```
- **Response**:
```json
{
  "score": 85,
  "matched_skills": ["Python", "Docker"],
  "missing_skills": ["Kubernetes"],
  "suggestions": ["Consider adding missing keywords to your resume to pass strict ATS filters: Kubernetes."],
  "semantic_score": 0.88
}
```

### 6. `POST /enhance_profile`
- **Auth**: Bearer JWT
- **Request Body**: Profile payload with `skills`, `projects`, `experience`, `certificates`.
- **Response**: `{"status": "success", "enhanced_profile": {...}}`

---

## Running Tests

Run pytest across all unit, integration, and constraint tests:

```bash
pytest services/ml/tests -v
```
