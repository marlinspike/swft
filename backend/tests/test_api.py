from __future__ import annotations

from fastapi.testclient import TestClient
from pathlib import Path
from app.main import create_app
from app.core.config import AppSettings, StorageSettings, AzureAuthSettings
from app.services.catalog import ArtifactCatalogService
from app.services.repository import LocalBlobRepository
from app.api import deps


def _seed(tmp_path: Path) -> None:
    data_dir = Path(__file__).parent / "data"
    for container in ("runs", "sboms", "scans", "appdesign"):
        dest = tmp_path / container
        dest.mkdir(parents=True, exist_ok=True)
        for file in (data_dir / container).glob("*"):
            dest_file = dest / file.name
            dest_file.write_text(file.read_text(), encoding="utf-8")


def _settings(tmp_path: Path) -> AppSettings:
    storage = StorageSettings(
        account_name=None,
        connection_string=None,
        container_sboms="sboms",
        container_scans="scans",
        container_runs="runs",
        container_appdesign="appdesign",
        delimiter="-",
        local_blob_root=str(tmp_path)
    )
    auth = AzureAuthSettings(tenant_id=None, client_id=None, client_secret=None)
    return AppSettings(storage=storage, auth=auth, cache_ttl_seconds=60, cache_max_items=64)


def test_projects_endpoint(tmp_path: Path) -> None:
    _seed(tmp_path)
    settings = _settings(tmp_path)
    repository = LocalBlobRepository(str(tmp_path))
    catalog = ArtifactCatalogService(repository, settings)
    app = create_app()

    app.dependency_overrides[deps.get_settings_dep] = lambda: settings
    app.dependency_overrides[deps.get_catalog] = lambda: catalog
    client = TestClient(app)
    response = client.get("/projects")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["project_id"] == "demo"


def test_runs_endpoint_returns_limited_history(tmp_path: Path) -> None:
    _seed(tmp_path)
    (tmp_path / "runs" / "demo-101-run.json").write_text(
        """{
  "id": "101",
  "projectName": "demo",
  "createdAt": "2024-08-01T12:00:00Z",
  "assessment": {
    "cosign": { "verifyStatus": "failed" },
    "trivy": { "findings": { "total": 9, "failSet": 2 } }
  }
}""",
        encoding="utf-8"
    )
    (tmp_path / "sboms" / "demo-101-sbom.json").write_text(
        """{ "bomFormat": "CycloneDX", "specVersion": "1.4", "components": [ { "name": "fastapi" }, { "name": "uvicorn" } ] }""",
        encoding="utf-8"
    )
    (tmp_path / "scans" / "demo-101-trivy.json").write_text("""{ "results": [] }""", encoding="utf-8")
    (tmp_path / "appdesign" / "demo-101-appdesign.md").write_text("# Demo design 101\n", encoding="utf-8")

    settings = _settings(tmp_path)
    repository = LocalBlobRepository(str(tmp_path))
    catalog = ArtifactCatalogService(repository, settings)
    app = create_app()

    app.dependency_overrides[deps.get_settings_dep] = lambda: settings
    app.dependency_overrides[deps.get_catalog] = lambda: catalog
    client = TestClient(app)

    response = client.get("/projects/demo/runs?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2  # only two runs exist
    assert data[0]["run_id"] == "101"
    assert data[0]["sbom_component_total"] == 2


def test_artifact_endpoint_returns_app_design(tmp_path: Path) -> None:
    _seed(tmp_path)
    settings = _settings(tmp_path)
    repository = LocalBlobRepository(str(tmp_path))
    catalog = ArtifactCatalogService(repository, settings)
    app = create_app()

    app.dependency_overrides[deps.get_settings_dep] = lambda: settings
    app.dependency_overrides[deps.get_catalog] = lambda: catalog
    client = TestClient(app)

    response = client.get("/projects/demo/runs/100/artifacts/appdesign")
    assert response.status_code == 200
    payload = response.json()
    assert "content" in payload
    assert "architecture" in payload["content"].lower()
