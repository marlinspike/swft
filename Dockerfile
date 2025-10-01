FROM python:3.11-slim AS builder

# Builder stage: install build tooling and create wheels for all deps
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m ensurepip --upgrade \
  && pip install --no-cache-dir --upgrade pip setuptools wheel \
  && pip wheel --no-cache-dir -r requirements.txt -w /wheels

FROM python:3.11-slim AS runtime

# Runtime stage: copy wheels only and install with no cache
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN python -m ensurepip --upgrade \
  && pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir /wheels/* \
  && rm -rf /wheels

# Copy application code
COPY app/ app/
COPY templates/ templates/
COPY static/ static/

# Expose port 80
EXPOSE 80

# Default command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]