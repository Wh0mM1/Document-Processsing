# ==============================================================================
# FinSight AI — Containerized Document Intelligence & Research Studio
# Multi-stage optimized Dockerfile with Tesseract OCR, PyMuPDF, and FastAPI
# ==============================================================================

FROM python:3.13-slim

# Set environment flags
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies: Tesseract OCR, system graphics libraries, and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast, reliable package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency specifications first to leverage Docker layer caching
COPY pyproject.toml requirements.txt ./

# Install Python dependencies into system environment
RUN uv pip install --system -r requirements.txt

# Copy application source code and static UI assets
COPY finsight_agent/ ./finsight_agent/
COPY static/ ./static/
COPY main.py .env.example ./

# Create persistent runtime data directories
RUN mkdir -p data/uploads data/reports data/documents

# Expose Web UI and REST API port
EXPOSE 8000

# Health check to ensure the API server is responsive
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/stats || exit 1

# Start the unified Web UI and API server
CMD ["python", "main.py"]
