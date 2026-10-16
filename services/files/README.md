# CareerLens Files Service

Standalone microservice responsible for file uploads, static asset serving, and PDF text extraction. Extracted from the CareerLens monolith.

## Endpoints

- `GET /health`: Healthcheck endpoint, returns `{"status": "ok"}`.
- `POST /upload`: Multipart file upload. Sanitises storage as `<uuid4><ext>`, rejects path traversal, validates extension (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.doc`, `.docx`), enforces `MAX_UPLOAD_MB` size limit, and returns `{"filename": <original_name>, "url": "<PUBLIC_PREFIX>/<uuid4><ext>"}`.
- `POST /extract_pdf`: Extracts plain text from an uploaded PDF binary using PyPDF2.
- `GET /uploads/{filename}`: Static file serving from the uploads directory.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `UPLOAD_DIR` | Filesystem path where uploaded files are stored | `/app/uploads` |
| `PUBLIC_PREFIX` | URL prefix returned in `/upload` responses | `/api/files/uploads` |
| `MAX_UPLOAD_MB` | Maximum allowed file size in megabytes | `10` |

## Local Development

### 1. Create and Activate Virtual Environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Service
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Running with Docker

### Build Docker Image
```bash
docker build -t careerlens-files ./services/files
```

### Run Container
```bash
docker run -d \
  --name careerlens-files \
  -p 8001:8000 \
  -e UPLOAD_DIR=/app/uploads \
  -e PUBLIC_PREFIX=/api/files/uploads \
  -e MAX_UPLOAD_MB=10 \
  careerlens-files
```

## Running Tests

Run the pytest suite:
```bash
pytest -v services/files/tests/test_files.py
```
Or inside a container:
```bash
docker run --rm careerlens-files pytest -v tests/test_files.py
```
