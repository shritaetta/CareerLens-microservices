FROM python:3.11-slim

# Prevent Python from writing bytecode and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/appuser/.cache/huggingface \
    DATASET_PATH=/data/Book2.xlsx \
    DB_PATH=users.db

WORKDIR /app

# Create non-root user and directories
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/uploads /data /home/appuser/.cache/huggingface && \
    chown -R appuser:appuser /app /data /home/appuser

# Install dependencies with CPU-only torch
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Switch to non-root user
USER appuser

# Pre-download the SentenceTransformer model at build time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application source code
COPY --chown=appuser:appuser . .

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
