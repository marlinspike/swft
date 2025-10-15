# -------- 1) Builder stage (Alpine) --------
FROM python:3.11-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Build deps for compiling Python wheels on Alpine (musl)

RUN apk add --no-cache \
    build-base \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

# Prebuild wheels for all requirements
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip wheel --no-cache-dir -r requirements.txt -w /wheels

# -------- 2) Runtime stage (Alpine) --------
FROM python:3.11-alpine AS runtime

# Runtime stage: copy wheels only and install with no cache
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime libs only (no compilers)
RUN apk add --no-cache \
    libstdc++ \
    libffi \
    openssl \
    tzdata

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
 && pip install --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

# Copy application code
COPY app/ app/
COPY templates/ templates/
COPY static/ static/

# Expose port 80
EXPOSE 80

# Default command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]