# ==============================================================================
# FastAPI Backend Dockerfile (Multi-stage build, Python 3.12-slim, Non-Root)
# ==============================================================================
# Purpose:
#   Builds a secure, hardened, minimal container image for the backend API.
#
# Highlights:
#   - python:3.12-slim base image for minimal attack surface and small image size.
#   - Multi-stage build separates build dependencies (gcc, libpq-dev) from runtime.
#   - Runs under non-root user (appuser:10001) for container security compliance.
#   - Native HEALTHCHECK instruction querying /healthz.
# ==============================================================================

# --- Stage 1: Build & Wheel Compiler ---
FROM python:3.14-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies into user directory with no cache
RUN pip install --no-cache-dir --user -r requirements.txt


# --- Stage 2: Final Minimal Runtime ---
FROM python:3.14-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Install libpq runtime for PostgreSQL connectivity and curl for container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root group and user (UID/GID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

# Copy installed Python packages from builder stage
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Copy application source code
COPY --chown=appuser:appgroup app /app/app

# Switch to non-root user
USER 10001:10001

EXPOSE 8000

# Native Docker container health check pointing to Kubernetes liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/healthz || exit 1

# Launch FastAPI app with Uvicorn ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
