FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/appuser/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/home/appuser/.cache/torch/sentence_transformers \
    DATASET_PATH=/app/data/Book2.xlsx \
    REDIS_URL=redis://localhost:6379/0 \
    JWT_ALGORITHM=HS256 \
    JWT_EXPIRE_MINUTES=60

WORKDIR /app

# Create non-root user and cache directory
RUN useradd -m -u 1000 appuser && \
    mkdir -p /home/appuser/.cache && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /home/appuser /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download SentenceTransformer model at build time as non-root user
USER appuser
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application source code
COPY --chown=appuser:appuser . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
