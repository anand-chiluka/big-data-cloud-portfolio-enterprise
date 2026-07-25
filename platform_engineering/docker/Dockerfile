# Multi-stage build for the data ingestion framework.
#
# HONESTY NOTE: this Dockerfile has been reviewed for correct syntax and
# follows standard multi-stage build practices, but `docker build` has
# not been run against it in this environment, since no Docker daemon
# is available here. It is standard Dockerfile syntax using the official
# python base image and should build cleanly with `docker build .` given
# a Docker daemon.

# --- Stage 1: build dependencies in an isolated layer ---
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies separately from runtime dependencies so the
# final image doesn't carry compiler toolchains it doesn't need at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Stage 2: minimal runtime image ---
FROM python:3.12-slim AS runtime

# Run as a non-root user. Running containers as root is one of the most
# common, most avoidable security findings in a container security scan.
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy only the installed packages from the builder stage, not the
# compiler toolchain used to build them.
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

# Health check: a simple import-and-exit check confirming the application
# code is importable and dependencies are correctly installed. A real
# service would expose a /healthz HTTP endpoint instead; this is the
# minimal equivalent for a batch/streaming worker with no HTTP server.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import src.consumer" || exit 1

ENTRYPOINT ["python3", "-m", "src.consumer"]
