# MedinovAI Chatbot - Backend Dockerfile
# HIPAA-compliant, secure Python backend for healthcare AI assistant

# Use official Python runtime as base image
FROM python:3.14-rc-slim-bookworm

# Metadata
LABEL maintainer="MedinovAI Team <dev@myonsitehealthcare.com>"
LABEL description="MedinovAI Chatbot - HIPAA-compliant AI healthcare assistant"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Create non-root user for security
RUN groupadd --gid 1000 medinovai && \
    useradd --uid 1000 --gid medinovai --shell /bin/bash --create-home medinovai

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    portaudio19-dev \
    python3-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/tmp /app/uploads && \
    chown -R medinovai:medinovai /app

# Copy application code
COPY --chown=medinovai:medinovai . .

# Remove development files and sensitive data
RUN rm -rf \
    .git \
    .pytest_cache \
    __pycache__ \
    *.pyc \
    *.pyo \
    *.pyd \
    .Python \
    .env* \
    .vscode \
    .idea \
    *.log

# Set permissions for security
RUN chmod -R 755 /app && \
    chmod -R 750 /app/logs && \
    find /app -name "*.py" -exec chmod 644 {} \; && \
    chmod +x /app/main.py

# Create health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:8000/api/health/live || exit 1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh && \
    chown medinovai:medinovai /app/healthcheck.sh

# Switch to non-root user
USER medinovai

# Expose ports
EXPOSE 8000 8001

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/healthcheck.sh

# Environment variables for production
ENV NODE_ENV=production \
    LOG_LEVEL=INFO \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    WEBSOCKET_PORT=8001

# Start command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"] 