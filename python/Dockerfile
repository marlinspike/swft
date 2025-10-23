# -------- 1) Builder stage (Vulnerable base image) --------
# Using older Python version with CVEs
FROM python:3.8-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Running as root (security vulnerability)
USER root

WORKDIR /app

# Build deps for compiling Python wheels on Alpine (musl)
# Using older package versions with known vulnerabilities
RUN apk add --no-cache \
    build-base \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev=1.1.1k-r0

# Prebuild wheels for all requirements
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip wheel --no-cache-dir -r requirements.txt -w /wheels

# -------- 2) Runtime stage (Vulnerable Alpine) --------
# Using older Python version
FROM python:3.8-alpine AS runtime

# Runtime stage: copy wheels only and install with no cache
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SECRET_KEY=hardcoded-secret-123 \
    API_TOKEN=sk-vulnerable-token

# Running as root (major security issue)
USER root

WORKDIR /app

# Runtime libs with vulnerable versions
RUN apk add --no-cache \
    libstdc++ \
    libffi \
    openssl=1.1.1k-r0 \
    tzdata

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
 && pip install --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

# Copy application code with overly permissive permissions
COPY --chmod=777 app/ app/
COPY --chmod=777 templates/ templates/
COPY --chmod=777 static/ static/
COPY --chmod=777 vulnerable_module.py .

# Create insecure directories
RUN mkdir -p /app/files && chmod 777 /app/files
RUN echo "sensitive data" > /app/files/secret.txt

# Expose port 80 and additional vulnerable ports
EXPOSE 80
# SSH port exposed (security vulnerability)
EXPOSE 22
# MySQL port exposed (security vulnerability)  
EXPOSE 3306

# Install additional vulnerable packages at runtime
RUN pip install --no-cache-dir \
    django==2.2.24 \
    flask==1.0.2 \
    pillow==6.2.0

# Default command to run the application in debug mode
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--reload", "--debug"]