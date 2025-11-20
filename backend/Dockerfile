# syntax=docker/dockerfile:1.7
##
# Multi-stage build for the SWFT backend.
# - Builder stage creates an isolated venv with only runtime deps installed from pyproject.
# - Runtime stage copies the venv, drops to a non-root user, and serves FastAPI via Uvicorn.
##

FROM python:3.11-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
# Build within the backend subdirectory to avoid setuptools picking up non-package folders.
WORKDIR /srv/app/backend
COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
# Create a dedicated virtualenv to carry into the runtime layer.
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir .

FROM python:3.11-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /srv/app
# Install patched system libraries flagged by the latest scan (xml/gnutls/glibc/icu/xslt/tiff/perl/krb5/openssl).
RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        libxml2 \
        libexpat1 \
        libgnutls30 \
        libc-bin \
        libc6 \
        libicu72 \
        libxslt1.1 \
        libtiff6 \
        libkrb5-3 \
        libkrb5support0 \
        libgssapi-krb5-2 \
        openssl \
        libssl3 \
        perl-base \
    && rm -rf /var/lib/apt/lists/*
# Run as an unprivileged user for better isolation.
RUN groupadd --system swft && useradd --system --gid swft swft
COPY --from=builder /opt/venv /opt/venv
# Application files and lookup data.
COPY backend/app ./app
COPY lookup ./lookup
USER swft
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
