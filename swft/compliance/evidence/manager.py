"""Persistence helpers for evidence ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..config import Config
from ..projects import ProjectRecord
from ..runs import ensure_run
from ..store import get_connection
from ..store.files import pin_source_file


@dataclass(slots=True)
class EvidenceRecord:
    id: int
    kind: str
    file_path: Path
    content_hash: str
    run_fk: int
    run_id: str


class EvidenceManager:
    def __init__(self, config: Config) -> None:
        self.config = config

    def ingest_file(
        self,
        *,
        project: ProjectRecord,
        run_id: str,
        kind: str,
        source: Path,
    ) -> EvidenceRecord:
        dest_dir = self._run_dir(project.key, run_id)
        stem = f"{project.key}-{run_id}-{source.stem}"
        pinned_path, digest = pin_source_file(source, dest_dir, stem)
        size_bytes = pinned_path.stat().st_size
        collected_at = datetime.now(timezone.utc).isoformat()
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            run_fk = ensure_run(conn, project_id=project.id, run_id=run_id)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO evidence_files (kind, file_path, content_hash, size_bytes, collected_at, run_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (content_hash)
                    DO UPDATE SET
                        kind = EXCLUDED.kind,
                        file_path = EXCLUDED.file_path,
                        size_bytes = EXCLUDED.size_bytes,
                        collected_at = EXCLUDED.collected_at,
                        run_id = EXCLUDED.run_id
                    RETURNING id
                    """,
                    (
                        kind,
                        str(pinned_path),
                        digest,
                        size_bytes,
                        collected_at,
                        run_id,
                    ),
                )
                evidence_id = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO run_evidence (run_fk, evidence_fk)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (run_fk, evidence_id),
                )
            conn.commit()
        return EvidenceRecord(
            id=evidence_id,
            kind=kind,
            file_path=pinned_path,
            content_hash=digest,
            run_fk=run_fk,
            run_id=run_id,
        )

    def _run_dir(self, project_key: str, run_id: str) -> Path:
        base = self.config.paths.store / "evidence" / project_key / run_id
        base.mkdir(parents=True, exist_ok=True)
        return base
