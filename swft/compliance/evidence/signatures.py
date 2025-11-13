"""Cosign/Sigstore signature ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import Config
from ..projects import ProjectRecord
from ..store import get_connection
from ..utils import json
from .manager import EvidenceManager, EvidenceRecord


@dataclass(slots=True)
class SignatureResult:
    digest: str
    verified: bool


def parse_signature_file(path: Path) -> dict:
    """Load the raw cosign JSON for validation/logging."""
    return json.loads(path.read_bytes())


class SignatureIngestor:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.manager = EvidenceManager(config)

    def ingest(
        self,
        *,
        project: ProjectRecord,
        run_id: str,
        signature_path: Path,
        digest: str,
        verified: bool,
    ) -> EvidenceRecord:
        # Load once to ensure valid JSON and to support future enrichment.
        parse_signature_file(signature_path)
        evidence = self.manager.ingest_file(
            project=project,
            run_id=run_id,
            kind="signature",
            source=signature_path,
        )
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO signatures (evidence_fk, image_digest, verified)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (evidence_fk)
                    DO UPDATE SET image_digest = excluded.image_digest,
                                  verified = excluded.verified
                    """,
                    (evidence.id, digest, verified),
                )
            conn.commit()
        return evidence

