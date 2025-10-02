# C# Hello World on Alpine (.NET 8)

This folder contains a minimal .NET 8 console app and a secure multi-stage Dockerfile based on Alpine.

## Build and run locally (PowerShell)

```powershell
# From repo root
cd c-sharp

# Build the image
docker build -t hello-csharp:latest -f Dockerfile .

# Run it
docker run --rm hello-csharp:latest
```

## CI

- GitHub Actions workflow at `.github/workflows/build-csharp-docker.yml` builds the image and runs a smoke test on PRs/pushes touching `c-sharp/**`.

## Notes

- Uses official base images: `mcr.microsoft.com/dotnet/sdk:8.0-alpine` and `mcr.microsoft.com/dotnet/runtime:8.0-alpine`.
- Multi-stage build keeps runtime minimal and runs as a non-root user.
- You can optionally push to Docker Hub by setting `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` repo secrets.

## CI/CD workflows: Differences

This repo includes several workflows relevant to the C# image, plus a broader SWFT pipeline. Here’s a quick comparison.

| Aspect | build-csharp-docker.yml | csharp-swft.yml | deploy.yml |
| --- | --- | --- | --- |
| Triggers | push+PR on `c-sharp/**` | push main+PR on `c-sharp/**`, manual | push main, manual (inputs) |
| Path filters | Yes | Yes | No |
| Build context | `./c-sharp` | `./c-sharp` | repo root (`.`) |
| Image name | local test image | `csharp-hello` | `fastapi-demo` |
| Push to registry | No (local only; optional Docker Hub) | Yes (ACR) | Yes (ACR) |
| Registry login | Optional Docker Hub | ACR user/pass | ACR user/pass |
| Tagging/labels | `docker/metadata-action` | simple SHA tag | simple SHA tag |
| Digest pinning | No | Yes | Yes |
| Cosign sign/verify | No | Yes (keys required) | Yes (keys required) |
| SBOM | No | Yes (CycloneDX) | Yes (CycloneDX) |
| Trivy JSON | No | Yes | Yes |
| Trivy SARIF + upload | No | Yes | Yes |
| Policy gate (jq) | No | Yes (severity fail set) | Yes (severity fail set) |
| Storage uploads | No | Yes (Azure RBAC) | Yes (Azure RBAC) |
| Run summary JSON | No | Yes | Yes |
| SWFT submit (stub) | No | Yes | — |
| Deploy to ACI | No | Yes (in-job) | Yes |
| Concurrency | Yes | Yes | — |

File paths:
- `.github/workflows/build-csharp-docker.yml` — quick PR CI and smoke test; no push or security scans by default.
- `.github/workflows/csharp-swft.yml` — hardened SWFT pipeline to ACR with Cosign, SBOM, Trivy (SARIF), RBAC uploads, policy gate, ACI.
- `.github/workflows/deploy.yml` — broader SWFT pipeline (targets repo root/`fastapi-demo` image), includes Cosign, SARIF, policy gate, RBAC uploads, ACI.

 
Tip: use `csharp-swft.yml` for opinionated security and uploads to ACR; keep `build-csharp-docker.yml` for fast PR checks.

## How to use these workflows

Below are quick-start steps for each pipeline.

### build-csharp-docker.yml (fast PR CI)

- Triggered automatically on pushes/PRs that touch `c-sharp/**`.
- Optional: set repo secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` to enable the optional push step.
- What it does: builds the Docker image locally, runs a smoke test (checks “Hello World” output), and optionally pushes to Docker Hub.

### csharp-swft.yml (CI/CD to ACR)

1) Configure repo secrets: `ACR_LOGIN_SERVER`, `ACR_USERNAME`, `ACR_PASSWORD`, `AZURE_CREDENTIALS`, `AZURE_STORAGE_ACCOUNT`.
2) Optional: add `COSIGN_KEY_B64` and `COSIGN_PUB_KEY_B64` for signing.
3) Optional: set `AZURE_RESOURCE_GROUP`, `AZURE_CONTAINER_NAME` for ACI.

- Triggers: push to main (path-filtered to `c-sharp/**`), PR touching `c-sharp/**`, or manual dispatch.
- Manual inputs: `image_name`, `deploy_to_aci`, `trivy_severity`, `trivy_ignore_unfixed`.
- Actions: builds and pushes to ACR with a SHA tag, signs/verifies (if keys), generates SBOM + Trivy JSON/SARIF, uploads SARIF to GitHub Security, uploads artifacts to Azure Storage (RBAC), enforces a severity policy, optionally deploys to ACI.



### deploy.yml (broader SWFT for repo root python application)

1) Configure secrets: `ACR_LOGIN_SERVER`, `ACR_USERNAME`, `ACR_PASSWORD`, `AZURE_CREDENTIALS`, `AZURE_STORAGE_ACCOUNT`.
2) Optional: `COSIGN_KEY_B64`, `COSIGN_PUB_KEY_B64`, `AZURE_RESOURCE_GROUP`, `AZURE_CONTAINER_NAME`.

- Triggers: push to main and manual.
- Actions: builds and pushes the root app image (named `fastapi-demo`), signs/verifies, SBOM + Trivy SARIF, RBAC uploads, policy gate, deploys to ACI.

Notes

- RBAC uploads require granting the Service Principal in `AZURE_CREDENTIALS` the “Storage Blob Data Contributor” role on the storage account.
- ACI deploy assumes an HTTP server on port 80. The C# app here is a console app; keep deploy toggles off unless you switch to a web server.
