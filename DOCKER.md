# Docker Multi-Stage Build Documentation

## Overview

This project uses a **multi-stage Docker build** to create an optimized production container. The build process separates dependency compilation from the runtime environment, resulting in a significantly smaller and more secure final image.

## Build Results

| Metric | Value |
|--------|-------|
| **Builder Image** | 652MB |
| **Runtime Image** | 233MB |
| **Size Reduction** | 64.3% (419MB saved) |
| **Build Tools in Runtime** | ❌ None |
| **Python Version** | 3.11 |

## Multi-Stage Architecture

### Stage 1: Builder
```dockerfile
FROM python:3.11-slim AS builder
```

**Purpose**: Compile Python dependencies with all necessary build tools.

**Contains**:
- `build-essential` (gcc, make, etc.)
- `gcc` compiler
- Python build tools (`setuptools`, `wheel`)
- Compiled wheel files for all dependencies

**Output**: `/wheels` directory with pre-compiled packages

### Stage 2: Runtime
```dockerfile
FROM python:3.11-slim AS runtime
```

**Purpose**: Minimal production environment with only runtime dependencies.

**Contains**:
- Python 3.11 runtime
- Pre-compiled wheels (copied from builder)
- Application code
- No build tools or compilers

**Result**: Clean, secure, production-ready image

## Benefits

### 1. **Smaller Image Size**
- 64% reduction in final image size
- Faster deployment and container startup
- Reduced storage and bandwidth costs

### 2. **Enhanced Security**
- No build tools (gcc, make) in production image
- Smaller attack surface
- Fewer potential vulnerabilities

### 3. **Better Layer Caching**
- Dependencies cached separately from application code
- Faster rebuilds when only code changes
- Optimized CI/CD pipeline performance

### 4. **Production-Ready**
- Clean separation of build-time and runtime dependencies
- Industry best practice for containerized applications
- Easier to audit and maintain

## Usage

### Build the Image

```bash
docker build -t swft:latest .
```

### Run the Container

```bash
docker run --rm -p 8080:80 --env-file .env swft:latest
```

Access the application at: `http://localhost:8080`

### Build Specific Stages

**Builder stage only** (for debugging):
```bash
docker build --target builder -t swft:builder .
```

**Runtime stage** (default):
```bash
docker build -t swft:runtime .
```

## Testing

Run the comprehensive test script to verify the multi-stage build:

```bash
powershell -ExecutionPolicy Bypass -File .\test-docker-build.ps1
```

The test script performs:
- ✅ Docker availability check
- ✅ Builder stage build
- ✅ Runtime stage build
- ✅ Image size comparison
- ✅ Build tools verification (ensures gcc not in runtime)
- ✅ Container startup test
- ✅ HTTP endpoint verification
- ✅ Resource usage monitoring

### Test Output Example

```
=== SWFT Multi-Stage Docker Build Test ===

--- Building Builder Stage ---
[OK] Builder stage built in 5.3s

--- Building Runtime Stage ---
[OK] Runtime stage built in 2.3s

--- Image Size Comparison ---
  Builder image:  652MB
  Runtime image:  233MB
[OK] Size reduction: 64.3% (saved 419 MB)

--- Testing HTTP Endpoint ---
[OK] HTTP 200 OK received
[OK] Application content verified

=== Test Summary ===
  Container tested: PASS
  HTTP endpoint:    PASS
```

## Dockerfile Breakdown

### Environment Variables
```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
```
- `PYTHONDONTWRITEBYTECODE`: Prevents `.pyc` file generation
- `PYTHONUNBUFFERED`: Ensures logs appear immediately

### Builder Stage Process
1. Install build dependencies (`build-essential`, `gcc`)
2. Copy `requirements.txt`
3. Build wheels for all dependencies (including transitive deps)
4. Store wheels in `/wheels` directory

### Runtime Stage Process
1. Start from clean `python:3.11-slim` base
2. Copy wheels from builder stage
3. Install wheels (no compilation needed)
4. Remove wheels to save space
5. Copy application code
6. Set up Uvicorn server

### Application Structure
```
/app
├── app/          # FastAPI application
├── templates/    # Jinja2 templates
└── static/       # Static assets
```

## Dependencies

Managed via `requirements.txt`:
- `fastapi>=0.109.0` - Web framework
- `uvicorn>=0.27.0` - ASGI server
- `jinja2>=3.1.2` - Template engine
- `python-dotenv>=1.0.0` - Environment management
- `pydantic>=2.11.0` - Data validation

## Docker Ignore

The `.dockerignore` file excludes:
- `.git/` - Version control
- `**/__pycache__/` - Python cache
- `**/*.pyc` - Compiled Python files
- `.env` - Environment secrets
- `.venv/` - Virtual environments
- Development files

## Production Deployment

### Docker Compose Example

```yaml
version: '3.8'
services:
  swft:
    build: .
    ports:
      - "80:80"
    env_file:
      - .env
    restart: unless-stopped
```

### Environment Variables

Required in `.env`:
```bash
# Add your environment variables here
OPENAI_API_KEY=your_key_here
```

### Health Check

Add to Dockerfile for production:
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:80/ || exit 1
```

## Troubleshooting

### Build Fails
```bash
# Check Docker is running
docker info

# Build with verbose output
docker build -t swft:test . --progress=plain
```

### Container Won't Start
```bash
# Check logs
docker logs swft-test

# Run interactively
docker run --rm -it swft:test /bin/bash
```

### Size Issues
```bash
# Inspect image layers
docker history swft:test

# Check for large files
docker run --rm swft:test du -sh /*
```

## Best Practices Implemented

✅ **Multi-stage build** - Separate build and runtime environments  
✅ **Minimal base image** - Using `python:3.11-slim`  
✅ **Layer caching** - Dependencies before application code  
✅ **No cache installs** - `--no-cache-dir` flag for pip  
✅ **Cleanup** - Remove apt lists and wheels after use  
✅ **Environment variables** - Proper Python configuration  
✅ **Security** - No build tools in production image  
✅ **Dockerignore** - Exclude unnecessary files  

## Maintenance

### Update Dependencies
```bash
# Update requirements.txt
pip freeze > requirements.txt

# Rebuild image
docker build -t swft:latest .
```

### Version Tagging
```bash
# Tag with version
docker build -t swft:v1.0.0 .
docker tag swft:v1.0.0 swft:latest
```

## Additional Resources

- [Docker Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Python Docker Best Practices](https://docs.docker.com/language/python/build-images/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/docker/)

---

**Last Updated**: 2025-09-30  
**Docker Version**: 28.4.0  
**Python Version**: 3.11
