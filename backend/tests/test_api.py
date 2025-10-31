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
    for container in ("runs", "sboms", "scans"):
        dest = tmp_path / container
        dest.mkdir(parents=True, exist_ok=True)
        for file in (data_dir / container).glob("*.json"):
            dest_file = dest / file.name
            dest_file.write_text(file.read_text(), encoding="utf-8")


def _settings(tmp_path: Path) -> AppSettings:
    storage = StorageSettings(
        account_name=None,
        connection_string=None,
        container_sboms="sboms",
        container_scans="scans",
        container_runs="runs",
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
