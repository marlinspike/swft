# Docker Quick Start Guide

## 🚀 Quick Commands

### Build
```bash
docker build -t swft:latest .
```

### Run
```bash
docker run --rm -p 8080:80 --env-file .env swft:latest
```

### Test Everything
```bash
powershell -ExecutionPolicy Bypass -File .\test-docker-build.ps1
```

## 📊 Build Stats

| Metric | Value |
|--------|-------|
| Builder Image | 652MB |
| Runtime Image | 233MB |
| Reduction | **64.3%** |
| Build Time | ~7.5s |

## 🔍 Verify Build

```bash
# Check image size
docker images swft:latest

# Verify no build tools
docker run --rm swft:latest which gcc
# Should fail (exit code 1)

# Check running containers
docker ps

# View logs
docker logs <container-id>
```

## Test Endpoints

```bash
# Health check
curl http://localhost:8080

# Or in PowerShell
Invoke-WebRequest http://localhost:8080
```

## Dev

```bash
# Build and run in one command
docker build -t swft:dev . && docker run --rm -p 8080:80 swft:dev

# Interactive shell
docker run --rm -it swft:latest /bin/bash

# View image layers
docker history swft:latest
```

## Cleanup

```bash
# Stop all containers
docker stop $(docker ps -q)

# Remove images
docker rmi swft:latest swft:builder

# Full cleanup (careful!)
docker system prune -a
```

## Files Created

- `Dockerfile` - Multi-stage build definition
- `test-docker-build.ps1` - Automated test script
- `DOCKER.md` - Full documentation
- `.dockerignore` - Build exclusions

## What Was Accomplished

1. ✅ Converted single-stage to multi-stage Dockerfile
2. ✅ Reduced image size by 64.3% (419MB saved)
3. ✅ Removed build tools from production image
4. ✅ Created comprehensive test script
5. ✅ Verified container runs and serves HTTP
6. ✅ Documented entire process

## Next Steps

- [ ] Push to container registry (ACR)
- [ ] Set up CI/CD pipeline
- [ ] Sign the container
- [ ] Scan using tools
- [ ] Configure production environment variables
- [ ] Set up monitoring and logging
