"""Trivy JSON ingestion."""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..projects import ProjectRecord
from ..store import get_connection
from .manager import EvidenceManager, EvidenceRecord
from .parsers import TrivyFinding, parse_trivy_report


class TrivyIngestor:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.manager = EvidenceManager(config)

    def ingest(
        self,
        *,
        project: ProjectRecord,
        run_id: str,
        trivy_path: Path,
        artifact_hint: str | None = None,
    ) -> tuple[EvidenceRecord, int]:
        findings = parse_trivy_report(trivy_path)
        if artifact_hint:
            for finding in findings:
                if not finding.artifact:
                    finding.artifact = artifact_hint
        evidence = self.manager.ingest_file(
            project=project,
            run_id=run_id,
            kind="trivy",
            source=trivy_path,
        )
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            with conn.cursor() as cur:
                cur.execute("DELETE FROM trivy_findings WHERE evidence_fk = %s", (evidence.id,))
                for finding in findings:
                    cur.execute(
                        """
                        INSERT INTO trivy_findings (
                            evidence_fk,
                            cve_id,
                            severity,
                            pkg,
                            installed_version,
                            fixed_version,
                            artifact,
                            path
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            evidence.id,
                            finding.cve_id,
                            finding.severity,
                            finding.pkg,
                            finding.installed_version,
                            finding.fixed_version,
                            finding.artifact,
                            finding.path,
                        ),
                    )
            conn.commit()
        return evidence, len(findings)
