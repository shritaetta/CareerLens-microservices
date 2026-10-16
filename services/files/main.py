import os
import io
import uuid
import PyPDF2
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

DEFAULT_UPLOAD_DIR = "/app/uploads"
DEFAULT_PUBLIC_PREFIX = "/api/files/uploads"
DEFAULT_MAX_UPLOAD_MB = 10.0

ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx"}

def get_upload_dir() -> str:
    path = os.getenv("UPLOAD_DIR", DEFAULT_UPLOAD_DIR)
    os.makedirs(path, exist_ok=True)
    return path

def get_public_prefix() -> str:
    return os.getenv("PUBLIC_PREFIX", DEFAULT_PUBLIC_PREFIX).strip()

def get_max_upload_bytes():
    try:
        max_mb = float(os.getenv("MAX_UPLOAD_MB", str(DEFAULT_MAX_UPLOAD_MB)))
    except ValueError:
        max_mb = DEFAULT_MAX_UPLOAD_MB
    return int(max_mb * 1024 * 1024), max_mb

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_upload_dir()
    yield

app = FastAPI(
    title="CareerLens Files Service",
    description="File upload, static serving, and PDF extraction service",
    version="1.0.0",
    lifespan=lifespan,
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DynamicUploadStaticFiles(StaticFiles):
    def lookup_path(self, path: str):
        target_dir = os.path.abspath(get_upload_dir())
        self.all_directories = [target_dir]
        return super().lookup_path(path)

# Static serving of the uploads directory at /uploads
public_prefix = get_public_prefix()
app.mount("/uploads", DynamicUploadStaticFiles(check_dir=False), name="uploads")

# Also mount public prefix if it represents an absolute URL path different from /uploads
if public_prefix and public_prefix.startswith("/") and public_prefix.rstrip("/") != "/uploads":
    app.mount(public_prefix.rstrip("/"), DynamicUploadStaticFiles(check_dir=False), name="public_uploads")

@app.get("/health")
def health():
    return {"status": "ok"}

def is_safe_filename(filename: str) -> bool:
    if not filename:
        return False
    # Reject directory traversal indicators and path separators
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    if os.path.basename(filename) != filename:
        return False
    if os.path.isabs(filename):
        return False
    return True

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Saves generic physical file with sanitised uuid4 name and returns URL"""
    if not file.filename or not is_safe_filename(file.filename):
        return JSONResponse(
            status_code=400,
            content={"error": "Path traversal detected or invalid filename", "detail": "Path traversal detected"}
        )

    orig_ext = os.path.splitext(file.filename)[1]
    ext = orig_ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"File extension '{ext}' is not allowed. Allowed: {sorted(list(ALLOWED_EXTENSIONS))}",
                "detail": f"File extension '{ext}' not allowed"
            }
        )

    max_bytes, max_mb = get_max_upload_bytes()
    content_chunks = []
    total_size = 0
    chunk_size = 1024 * 64

    try:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": f"File size exceeds maximum allowed limit of {max_mb} MB",
                        "detail": f"File size exceeds limit of {max_mb} MB"
                    }
                )
            content_chunks.append(chunk)

        saved_filename = f"{uuid.uuid4()}{orig_ext}"
        target_dir = get_upload_dir()
        file_path = os.path.join(target_dir, saved_filename)

        with open(file_path, "wb") as buffer:
            for chunk in content_chunks:
                buffer.write(chunk)

        clean_prefix = get_public_prefix().rstrip("/")
        url = f"{clean_prefix}/{saved_filename}"

        return {
            "filename": file.filename,
            "url": url
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "detail": str(e)}
        )

@app.post("/extract_pdf")
async def extract_pdf_text(file: UploadFile = File(...)):
    """Extracts raw string text from an uploaded PDF binary"""
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        return {"error": "Uploaded file must be a PDF document."}
        
    try:
        content = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        return {"filename": file.filename, "extracted_text": text.strip()}
    except Exception as e:
        return {"error": str(e)}
