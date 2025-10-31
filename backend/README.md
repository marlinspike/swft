# SWFT Backend

FastAPI-based API that surfaces SWFT pipeline outputs directly from Azure Blob Storage. The service provides project, run, and artifact views used by the portal frontend.

## Local Development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

Copy `.env.example` to `.env` and update the values, or export them directly in your shell:

- `AZURE_STORAGE_ACCOUNT` — storage account name (or connection string when using `AZURE_STORAGE_CONNECTION_STRING`)
- `AZURE_STORAGE_CONNECTION_STRING` — optional connection string (takes precedence)
- `AZURE_STORAGE_CONTAINER_SBOMS` — container name for SBOM blobs (default `sboms`)
- `AZURE_STORAGE_CONTAINER_SCANS` — container name for Trivy scan blobs (default `scans`)
- `AZURE_STORAGE_CONTAINER_RUNS` — container name for run manifests (default `runs`)
- `AZURE_STORAGE_BLOB_PREFIX_DELIMITER` — delimiter between project and run identifiers (default `-`)
- `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` — optional service principal credentials; otherwise managed identity/CLI auth is used
- `LOCAL_BLOB_ROOT` — optional filesystem path for offline development; when set the service reads blobs from disk instead of Azure

## Testing

```bash
pytest
```

## Packaging

A container image can be built from the repository root:

```bash
docker build -t swft-backend -f backend/Dockerfile backend
```
