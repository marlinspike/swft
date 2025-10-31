from __future__ import annotations

from app.core.config import AppSettings, StorageSettings, AzureAuthSettings
from app.services.catalog import ArtifactCatalogService
from app.services.repository import LocalBlobRepository
from pathlib import Path


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


def test_catalog_lists_projects(tmp_path: Path) -> None:
    data_dir = Path(__file__).parent / "data"
    for container in ("runs", "sboms", "scans"):
        dest = tmp_path / container
        dest.mkdir(parents=True, exist_ok=True)
        for file in (data_dir / container).glob("*.json"):
            dest_file = dest / file.name
            dest_file.write_text(file.read_text(), encoding="utf-8")
    repository = LocalBlobRepository(str(tmp_path))
    service = ArtifactCatalogService(repository, _settings(tmp_path))

    projects = service.list_projects()
    assert len(projects) == 1
    assert projects[0].project_id == "demo"


def test_catalog_returns_run_detail(tmp_path: Path) -> None:
    data_dir = Path(__file__).parent / "data"
    for container in ("runs", "sboms", "scans"):
        dest = tmp_path / container
        dest.mkdir(parents=True, exist_ok=True)
        for file in (data_dir / container).glob("*.json"):
            dest_file = dest / file.name
            dest_file.write_text(file.read_text(), encoding="utf-8")
    repository = LocalBlobRepository(str(tmp_path))
    service = ArtifactCatalogService(repository, _settings(tmp_path))

    detail = service.run_detail("demo", "100")
    assert detail.summary.project_id == "demo"
    assert detail.summary.run_id == "100"
    assert detail.summary.cosign_status == "passed"
