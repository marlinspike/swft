"""CycloneDX SBOM ingestion."""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..projects import ProjectRecord
from ..store import get_connection
from .manager import EvidenceManager, EvidenceRecord
from .parsers import SbomComponent, parse_cyclonedx


class SbomIngestor:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.manager = EvidenceManager(config)

    def ingest(self, *, project: ProjectRecord, run_id: str, sbom_path: Path) -> tuple[EvidenceRecord, int]:
        components = parse_cyclonedx(sbom_path)
        evidence = self.manager.ingest_file(
            project=project,
            run_id=run_id,
            kind="sbom",
            source=sbom_path,
        )
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            with conn.cursor() as cur:
                cur.execute("DELETE FROM sbom_components WHERE evidence_fk = %s", (evidence.id,))
                for component in components:
                    cur.execute(
                        """
                        INSERT INTO sbom_components (evidence_fk, name, version, purl, licenses)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            evidence.id,
                            component.name,
                            component.version,
                            component.purl,
                            ", ".join(component.licenses),
                        ),
                    )
            conn.commit()
        return evidence, len(components)

