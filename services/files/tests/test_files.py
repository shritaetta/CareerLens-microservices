import io
import os
import pytest
from fastapi.testclient import TestClient
import PyPDF2

from main import app, ALLOWED_EXTENSIONS

@pytest.fixture
def client(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("PUBLIC_PREFIX", "/api/files/uploads")
    monkeypatch.setenv("MAX_UPLOAD_MB", "10")
    
    with TestClient(app) as test_client:
        yield test_client

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_upload_valid_pdf(client):
    file_content = b"%PDF-1.4 test document content"
    files = {"file": ("my_resume.pdf", io.BytesIO(file_content), "application/pdf")}
    
    response = client.post("/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "my_resume.pdf"
    assert data["url"].startswith("/api/files/uploads/")
    assert data["url"].endswith(".pdf")

def test_static_file_serving(client):
    file_content = b"%PDF-1.4 file content to verify static serving"
    files = {"file": ("static_test.pdf", io.BytesIO(file_content), "application/pdf")}
    upload_res = client.post("/upload", files=files)
    assert upload_res.status_code == 200
    file_url = upload_res.json()["url"]
    
    # Test fetch via returned URL (PUBLIC_PREFIX)
    get_res = client.get(file_url)
    assert get_res.status_code == 200
    assert get_res.content == file_content
    
    # Test fetch via /uploads endpoint
    saved_filename = file_url.split("/")[-1]
    direct_res = client.get(f"/uploads/{saved_filename}")
    assert direct_res.status_code == 200
    assert direct_res.content == file_content

def test_upload_allowed_extensions(client):
    for ext in [".png", ".jpg", ".jpeg", ".doc", ".docx"]:
        content = b"sample binary content"
        filename = f"document{ext}"
        files = {"file": (filename, io.BytesIO(content), "application/octet-stream")}
        response = client.post("/upload", files=files)
        assert response.status_code == 200, f"Failed for extension {ext}"
        assert response.json()["filename"] == filename
        assert response.json()["url"].endswith(ext)

def test_upload_disallowed_extension(client):
    for ext in [".exe", ".sh", ".py", ".html", ".bat"]:
        content = b"echo dangerous"
        filename = f"danger{ext}"
        files = {"file": (filename, io.BytesIO(content), "application/octet-stream")}
        response = client.post("/upload", files=files)
        assert response.status_code == 400
        assert "not allowed" in response.json().get("error", "").lower()

def test_upload_traversal_rejection(client):
    traversal_filenames = [
        "../../etc/passwd.pdf",
        "..\\..\\windows\\system32\\calc.exe.pdf",
        "subfolder/nested.pdf",
        "nested\\file.pdf",
        "../test.pdf",
        "..\\test.pdf",
    ]
    for filename in traversal_filenames:
        files = {"file": (filename, io.BytesIO(b"content"), "application/pdf")}
        response = client.post("/upload", files=files)
        assert response.status_code == 400, f"Failed to reject traversal for {filename}"
        assert "path traversal" in response.json().get("error", "").lower()

def test_upload_oversize_rejection(client, monkeypatch):
    # Set limit to 0.001 MB (~1 KB)
    monkeypatch.setenv("MAX_UPLOAD_MB", "0.001")
    large_content = b"A" * 5000  # ~5 KB
    files = {"file": ("large_file.pdf", io.BytesIO(large_content), "application/pdf")}
    
    response = client.post("/upload", files=files)
    assert response.status_code == 413
    assert "exceeds" in response.json().get("error", "").lower()

def test_extract_pdf_valid(client):
    # Create valid minimal PDF using PyPDF2
    writer = PyPDF2.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    stream = io.BytesIO()
    writer.write(stream)
    pdf_bytes = stream.getvalue()

    files = {"file": ("test_doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/extract_pdf", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_doc.pdf"
    assert "extracted_text" in data

def test_extract_pdf_non_pdf(client):
    files = {"file": ("notes.txt", io.BytesIO(b"plain text content"), "text/plain")}
    response = client.post("/extract_pdf", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert "must be a pdf" in data["error"].lower()

def test_extract_pdf_corrupt(client):
    files = {"file": ("corrupt.pdf", io.BytesIO(b"not a valid pdf content"), "application/pdf")}
    response = client.post("/extract_pdf", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
