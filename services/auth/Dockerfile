FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create non-root user and assign permissions
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER appuser

# Copy application source code
COPY --chown=appuser:appuser . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
