# Backend Dockerfile
# Security-hardened for production use

FROM python:3.12-slim

# Security: Add metadata labels
LABEL maintainer="CronBox Team"
LABEL version="1.0"
LABEL description="CronBox Backend API Server"

# Security: Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_NO_DEV=1

# Install uv package manager
RUN pip install --no-cache-dir uv

# Security: Create non-root user for running the application
RUN groupadd --gid 1000 cronbox && \
    useradd --uid 1000 --gid cronbox --shell /bin/bash --create-home cronbox

# Set working directory
WORKDIR /app

# Copy dependency files first (for better layer caching)
COPY --chown=cronbox:cronbox pyproject.toml uv.lock ./

# Install dependencies with cache mount (survives image prune)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev && \
    chown -R cronbox:cronbox /app/.venv

# Copy application code with proper ownership
COPY --chown=cronbox:cronbox app ./app
COPY --chown=cronbox:cronbox alembic ./alembic
COPY --chown=cronbox:cronbox alembic.ini ./

# Create uploads directory and set permissions
RUN mkdir -p /app/uploads && \
    chown -R cronbox:cronbox /app/uploads && \
    chmod -R 755 /app && \
    find /app -type f -name "*.py" -exec chmod 644 {} \;

# Security: Switch to non-root user
USER cronbox

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
