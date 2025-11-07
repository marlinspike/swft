# syntax=docker/dockerfile:1.7
##
# Multi-stage build for the SWFT backend.
# - Builder stage creates an isolated venv with only runtime deps installed from pyproject.
# - Runtime stage copies the venv, drops to a non-root user, and serves FastAPI via Uvicorn.
##

FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /srv/app
COPY pyproject.toml README.md ./
COPY app ./app
# Create a dedicated virtualenv to carry into the runtime layer.
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir .

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /srv/app
# Run as an unprivileged user for better isolation.
RUN groupadd --system swft && useradd --system --gid swft swft
COPY --from=builder /opt/venv /opt/venv
# Application files are copied for logging/templates that may be read at runtime.
COPY app ./app
USER swft
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
