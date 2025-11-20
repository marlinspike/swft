"""Importer for Azure Policy initiatives."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from psycopg import sql

from ...config import Config
from ...store import get_connection
from ...store.files import pin_source_file
from ...store.versioning import ensure_version, VersionRecord
from ...utils.strings import slugify
from .parser import load_initiative, InitiativePolicy


SCOPE_VALUES = {"commercial", "gov"}


@dataclass(slots=True)
class InitiativeImportResult:
    version: VersionRecord
    initiative_id: int
    policy_count: int
    mapping_count: int
    pinned_path: Path


class PolicyDefinitionImporter:
    def __init__(self, config: Config) -> None:
        self.config = config

    def ingest(
        self,
        *,
        file_path: Path,
        name: str,
        scope: str,
    ) -> InitiativeImportResult:
        scope = scope.lower()
        if scope not in SCOPE_VALUES:
            raise ValueError("Scope must be 'commercial' or 'gov'.")
        document = load_initiative(file_path)
        slug = slugify(name, default=name)
        dest_dir = self.config.paths.pinned / "policy_initiatives"
        pinned_path, digest = pin_source_file(file_path, dest_dir, slug)
        version_label = document.version or name
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            version = ensure_version(
                conn,
                kind="policy_initiative",
                name=name,
                version=version_label,
                content_hash=digest,
                source_uri=str(pinned_path),
            )
            initiative_fk = self._ensure_initiative(conn, name=name, scope=scope, version_ref=version.id)
            policy_count, mapping_count = self._upsert_policies(conn, initiative_fk, document.policies)
            conn.commit()
        return InitiativeImportResult(
            version=version,
            initiative_id=initiative_fk,
            policy_count=policy_count,
            mapping_count=mapping_count,
            pinned_path=pinned_path,
        )

    def _ensure_initiative(self, conn, *, name: str, scope: str, version_ref: int) -> int:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM policy_initiatives
                WHERE initiative_id = %s AND scope = %s
                """,
                (name, scope),
            )
            row = cur.fetchone()
            if row:
                initiative_id = row[0]
                cur.execute(
                    "UPDATE policy_initiatives SET initiative_version_ref = %s WHERE id = %s",
                    (version_ref, initiative_id),
                )
                return initiative_id
            cur.execute(
                """
                INSERT INTO policy_initiatives (initiative_id, scope, initiative_version_ref)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (name, scope, version_ref),
            )
            return cur.fetchone()[0]

    def _upsert_policies(self, conn, initiative_fk: int, policies: list[InitiativePolicy]) -> tuple[int, int]:
        policy_count = 0
        mapping_count = 0
        with conn.cursor() as cur:
            cur.execute("DELETE FROM policy_mappings WHERE initiative_fk = %s", (initiative_fk,))
            for policy in policies:
                policy_count += 1
                cur.execute(
                    """
                    INSERT INTO policy_definitions (policy_definition_id, display_name, category)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (policy_definition_id)
                    DO UPDATE SET display_name = EXCLUDED.display_name,
                                  category = EXCLUDED.category
                    """,
                    (policy.policy_definition_id, policy.display_name, policy.category),
                )
                for control_id in policy.control_ids:
                    cur.execute(
                        """
                        INSERT INTO policy_mappings (initiative_fk, control_id, policy_definition_fk)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (initiative_fk, control_id, policy.policy_definition_id),
                    )
                    mapping_count += 1
        return policy_count, mapping_count
