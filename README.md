# FastAPI + Tailwind Demo (SWFT)

A small FastAPI app with a Tailwind-styled UI and a security-focused CI/CD pipeline. The workflow builds, signs, scans, uploads artifacts, and deploys to Azure Container Instances (ACI).

## What’s inside

- Demo workload with Python FastAPI w/ Tailwind-styled HTML UI
- Live time and container ID display
- Health and time endpoints
- Containerized app (Dockerfile) listening on port 80
- Supply-chain controls (SWFT-inspired pipeline):
   - SBOM (Syft via Anchore)
   - Vulnerability scanning (Trivy: JSON + SARIF)
   - Image signing and verification (Cosign)
   - Optional uploads to Azure Storage
   - SARIF published to GitHub Code Scanning

## Quickstart (local)

Prereqs: Python 3.11+, pip

1) Install deps
```bash
pip install -r requirements.txt
```

2) Run the dev server (use a non-privileged port locally)
```bash
uvicorn app.main:app --reload --port 8080
```

Now visit http://localhost:8080

Environment variables you can set locally:
- `BACKGROUND_COLOR` (default: `white`)
- `CUSTOM_MESSAGE` (default: `SWFT Demo`)

## Run with Docker

Build:
```bash
docker build -t swft-demo .
```

Run (container listens on 80; map to 8080 on your machine):
```bash
docker run -p 8080:80 \
   -e BACKGROUND_COLOR=blue \
   -e CUSTOM_MESSAGE="My Custom Message" \
   swft-demo
```

## CI/CD with GitHub Actions

Workflow: `.github/workflows/deploy.yml`

On push to `main` or manual dispatch, the pipeline will:
1. Build and push the image to ACR
2. Pull by tag and capture the image digest
3. Sign the image (by digest) with Cosign
4. Generate SBOM (CycloneDX JSON)
5. Scan with Trivy (JSON + SARIF)
6. Enforce policy thresholds (optional)
7. Upload SARIF to GitHub Code Scanning
8. Optionally upload SBOM/scan/run JSON to Azure Blob Storage
9. Deploy to Azure Container Instances and publish the public URL
10. Upload key files as GitHub Artifacts

### Required GitHub secrets

Add these repository secrets before running the workflow:

- `ACR_LOGIN_SERVER` — e.g., `myregistry.azurecr.io`
- `ACR_USERNAME` — ACR username (often the ACR name)
- `ACR_PASSWORD` — ACR password
- `IMAGE_TAG` — Tag to use for the pushed image (e.g., `main-${{ github.run_number }}` or a fixed value)
- `AZURE_CREDENTIALS` — JSON for `azure/login@v2` (ClientId, TenantId, SubscriptionId, and auth)
- `AZURE_STORAGE_ACCOUNT` — Name of the storage account for uploads
- `COSIGN_KEY_B64` — base64-encoded private key (cosign.key)
- `COSIGN_PUB_KEY_B64` — base64-encoded public key (cosign.pub)

> Note: This workflow uses OIDC-compatible `azure/login@v2`. Ensure your credentials and federated identity are set up per Azure login docs.

### Optional repository variables

These repo-level “Variables” (not secrets) influence push runs (no manual inputs needed):

- `PROJECT_NAME` — logical name for grouping artifacts (defaults to repo name)
- `UPLOAD_TO_AZURE` — `true|false` (default: `true` if unset)
- `UPLOAD_ARTIFACTS` — `true|false` (default: `true` if unset)
- `FAIL_ON_TRIVY` — `true|false` (default: `false`)

### Manual dispatch inputs

When you run the workflow manually, you can override behavior via inputs:

- `project_name` — logical name used in filenames
- `upload_to_azure` — upload SBOM/scan/run JSON to Azure Storage
- `upload_artifacts` — upload files as GitHub Artifacts
- `trivy_config` — semicolon-separated options: `scan=<levels>;ignore_unfixed=<true|false>;fail=<levels>`
   - Example: `scan=HIGH,CRITICAL;ignore_unfixed=true;fail=CRITICAL`
- `storage_containers` — CSV: `sboms,scans,runs` (container names)
- `fail_on_trivy` — if `true`, fail the job when any finding in the `fail` set exists
- `fail_on_cosign_verify` — if `true`, fail the job when signature verification fails

### What gets produced (files and where to find them)

Fixed filenames generated in the workspace:
- `sbom.cyclonedx.json` — SBOM (CycloneDX JSON)
- `trivy-report.json` — Trivy JSON results
- `trivy-results.sarif` — Trivy SARIF (uploaded to Code Scanning)
- `aci-endpoint.txt` — Public URL after ACI deploy
- `run.json` — Rich run metadata (links, image details, policy findings)

When Azure uploads are enabled, files are uploaded with flat names using a prefix:
```
<project_name>-<run_id>-sbom.json
<project_name>-<run_id>-trivy.json
<project_name>-<run_id>-run.json
```
Container names default to `sboms`, `scans`, `runs` (configurable via input/variables). The job prints the blob URLs in the summary.

Artifacts uploaded to GitHub (names include `PROJECT_NAME` and `RUN_ID`):
- `sbom-<project>-<runId>` → `sbom.cyclonedx.json`
- `trivy-json-<project>-<runId>` → `trivy-report.json`
- `trivy-sarif-<project>-<runId>` → `trivy-results.sarif`
- `aci-deploy-info-<project>-<runId>` → `aci-endpoint.txt`
- `swft-run-json-<project>-<runId>` → `run.json`

GitHub Security (Code scanning):
- The workflow uploads Trivy SARIF so you can review findings under “Security → Code scanning alerts”.

### Azure deployment

The workflow deploys to Azure Container Instances (ACI) using:

- Resource group (env): `AZURE_RESOURCE_GROUP` (default in workflow: `demo-swft-cicd`)
- Container group name (env): `AZURE_CONTAINER_NAME` (default: `swft-fastapi`)
- Image: `${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}`

Once deployed, it writes the public URL to `aci-endpoint.txt` and includes it in the job summary.

## Cosign key setup (for CI/CD)

1) Install Cosign (see Sigstore docs) and generate a keypair:
```bash
cosign generate-key-pair
```

2) Base64-encode both keys so the workflow can decode them:
```bash
base64 -i cosign.key | tr -d '\n' > cosign.key.b64
base64 -i cosign.pub | tr -d '\n' > cosign.pub.b64
```

3) Add these contents as repository secrets:
- `COSIGN_KEY_B64` ← contents of `cosign.key.b64`
- `COSIGN_PUB_KEY_B64` ← contents of `cosign.pub.b64`

The workflow signs the image by digest and verifies with the public key. You can choose to fail the run if verification fails using `fail_on_cosign_verify`.

## Endpoints

- `GET /` — Main page with dynamic content
- `GET /health` — Health check
- `GET /time` — Current server time

## Troubleshooting

- Local port 80 requires elevated privileges on some OSes. Use `--port 8080` with uvicorn and map `8080:80` for Docker.
- If SARIF isn’t visible, ensure you have permission to view Code scanning and that the workflow ran on the default branch or a branch supported by your repository’s security settings.
- Azure uploads require the storage account to exist and the identity used by `azure/login` to have proper RBAC (e.g., Storage Blob Data Contributor on the account).
- Trivy ACR auth: the workflow passes ACR creds via env; ensure they’re valid and that the image tag exists.

## License

MIT License