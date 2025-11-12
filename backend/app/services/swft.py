from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable

from swft.compliance.config import Config as SwftConfig, load_config
from swft.compliance.projects import ProjectsManager, ProjectRecord
from swft.compliance.controls import ControlService, ControlParameter
from swft.compliance.importers.oscal.catalog_importer import CatalogImporter
from swft.compliance.importers.oscal.profile_importer import ProfileImporter
from swft.compliance.importers.azure.policy_definition_importer import PolicyDefinitionImporter
from swft.compliance.importers.azure.policy_state_importer import PolicyStateImporter
from swft.compliance.evidence.sbom_cyclonedx import SbomIngestor
from swft.compliance.evidence.trivy import TrivyIngestor
from swft.compliance.evidence.signatures import SignatureIngestor
from swft.compliance.mapping import ensure_implemented_requirement
from swft.compliance.store import get_connection
from .azure_services import get_azure_services, get_azure_service_lookup
from .azure_regions import get_azure_regions, get_azure_region_lookup


class SwftComplianceService:
    """Facade around the CLI-oriented compliance modules for API use."""

    def __init__(self, config: SwftConfig | None = None) -> None:
        self.config = config or load_config()
        self.projects = ProjectsManager(self.config)
        self.control_service = ControlService(self.config)
        self.catalog_importer = CatalogImporter(self.config)
        self.profile_importer = ProfileImporter(self.config)
        self.policy_definition_importer = PolicyDefinitionImporter(self.config)
        self.policy_state_importer = PolicyStateImporter(self.config)
        self.sbom_ingestor = SbomIngestor(self.config)
        self.trivy_ingestor = TrivyIngestor(self.config)
        self.signature_ingestor = SignatureIngestor(self.config)
        self._service_lookup = get_azure_service_lookup()
        self._region_lookup = get_azure_region_lookup()

    # --- Authoritative catalog + policy imports -------------------------------------------------

    def sync_catalog(self, *, catalog_path: Path, baseline_path: Path, baseline_name: str, catalog_name: str) -> tuple[dict, dict]:
        """Ingest the OSCAL catalog and baseline profile."""
        catalog_result = self.catalog_importer.ingest(catalog_path=catalog_path, name=catalog_name)
        baseline_result = self.profile_importer.ingest(profile_path=baseline_path, profile_name=baseline_name)
        return (
            {
                "name": catalog_name,
                "controls": catalog_result.control_count,
                "version": catalog_result.version.version,
            },
            {
                "name": baseline_name,
                "controls": baseline_result.control_count,
                "version": baseline_result.version.version,
            },
        )

    def import_policy_initiative(self, *, file_path: Path, name: str, scope: str) -> dict:
        result = self.policy_definition_importer.ingest(file_path=file_path, name=name, scope=scope)
        return {
            "initiative": name,
            "scope": scope,
            "policies": result.policy_count,
            "mappings": result.mapping_count,
            "version": result.version.version,
        }

    def import_policy_states(self, *, file_path: Path, initiative: str, scope: str) -> dict:
        result = self.policy_state_importer.ingest(file_path=file_path, initiative_name=initiative, scope=scope)
        return {"processed": result.rows_processed, "inserted": result.rows_inserted}

    # --- Project + parameter management ---------------------------------------------------------

    def upsert_project(self, *, project_key: str, services: Iterable[str], regions: Iterable[str], boundary: str | None) -> ProjectRecord:
        normalized_services = self._normalize_services(services)
        normalized_regions = self._normalize_regions(regions)
        return self.projects.upsert_project(
            key=project_key,
            services=normalized_services,
            regions=normalized_regions,
            boundary_description=boundary,
        )

    def get_project(self, *, project_key: str) -> ProjectRecord:
        return self.projects.get_project(project_key)

    def list_parameters(self, *, project_key: str, control_id: str) -> list[ControlParameter]:
        project = self.projects.get_project(project_key)
        return self.control_service.list_parameters(control_id, project_id=project.id)

    def set_parameter(self, *, project_key: str, control_id: str, param_id: str, value: str) -> None:
        project = self.projects.get_project(project_key)
        self.control_service.ensure_parameter_exists(control_id, param_id)
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO parameter_values (project_fk, control_id, param_id, value)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (project_fk, control_id, param_id)
                    DO UPDATE SET value = excluded.value
                    """,
                    (project.id, control_id, param_id, value),
                )
                ensure_implemented_requirement(conn, project_id=project.id, control_id=control_id)
        conn.commit()

    def _normalize_services(self, services: Iterable[str]) -> list[str]:
        cleaned = [svc.strip() for svc in services if svc.strip()]
        if not self._service_lookup:
            return cleaned
        invalid: list[str] = []
        normalized: list[str] = []
        for entry in cleaned:
            canonical = self._service_lookup.get(entry.lower())
            if canonical:
                if canonical not in normalized:
                    normalized.append(canonical)
            else:
                invalid.append(entry)
        if invalid:
            raise ValueError(f"Unknown Azure service(s): {', '.join(invalid)}. Please select from the published Azure service catalog.")
        return normalized

    def _normalize_regions(self, regions: Iterable[str]) -> list[str]:
        cleaned = [reg.strip() for reg in regions if reg.strip()]
        if not self._region_lookup:
            return cleaned
        invalid: list[str] = []
        normalized: list[str] = []
        for entry in cleaned:
            canonical = self._region_lookup.get(entry.lower())
            if canonical:
                if canonical not in normalized:
                    normalized.append(canonical)
            else:
                invalid.append(entry)
        if invalid:
            raise ValueError(f"Unknown Azure region(s): {', '.join(invalid)}. Please select from the official Azure region catalog.")
        return normalized

    # --- Evidence ingestion ---------------------------------------------------------------------

    def ingest_sbom(self, *, project_key: str, run_id: str, sbom_path: Path) -> dict:
        project = self.projects.get_project(project_key)
        evidence, count = self.sbom_ingestor.ingest(project=project, run_id=run_id, sbom_path=sbom_path)
        return {"evidence_id": evidence.id, "run_id": run_id, "kind": "sbom", "components": count}

    def ingest_trivy(self, *, project_key: str, run_id: str, report_path: Path, artifact_hint: str | None) -> dict:
        project = self.projects.get_project(project_key)
        evidence, count = self.trivy_ingestor.ingest(project=project, run_id=run_id, trivy_path=report_path, artifact_hint=artifact_hint)
        return {"evidence_id": evidence.id, "run_id": run_id, "kind": "trivy", "findings": count}

    def ingest_signature(self, *, project_key: str, run_id: str, signature_path: Path, digest: str, verified: bool) -> dict:
        project = self.projects.get_project(project_key)
        evidence = self.signature_ingestor.ingest(project=project, run_id=run_id, signature_path=signature_path, digest=digest, verified=verified)
        return {"evidence_id": evidence.id, "run_id": run_id, "kind": "signature", "verified": verified}

    def list_azure_services(self) -> list[str]:
        return get_azure_services()

    def list_azure_regions(self) -> list[str]:
        return get_azure_regions()


@lru_cache
def get_swft_service() -> SwftComplianceService:
    """FastAPI dependency wrapper."""
    return SwftComplianceService()
