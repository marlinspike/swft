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
    assert detail.summary.sbom_component_total == 1


def test_catalog_list_runs_limit(tmp_path: Path) -> None:
    data_dir = Path(__file__).parent / "data"
    for container in ("runs", "sboms", "scans"):
        dest = tmp_path / container
        dest.mkdir(parents=True, exist_ok=True)
        for file in (data_dir / container).glob("*.json"):
            dest_file = dest / file.name
            dest_file.write_text(file.read_text(), encoding="utf-8")
    # add a newer run with distinct metrics
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
    (tmp_path / "scans" / "demo-101-trivy.json").write_text(
        """{ "results": [] }""",
        encoding="utf-8"
    )

    repository = LocalBlobRepository(str(tmp_path))
    service = ArtifactCatalogService(repository, _settings(tmp_path))

    limited = service.list_runs("demo", limit=2)
    assert len(limited) == 2
    assert limited[0].run_id == "101"
    assert limited[0].sbom_component_total == 2
    assert limited[1].run_id == "100"
