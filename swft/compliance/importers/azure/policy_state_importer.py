"""Importer for Azure Policy state snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ...config import Config
from ...store import get_connection
from .parser import load_policy_states, PolicyStateEntry


@dataclass(slots=True)
class PolicyStateImportResult:
    rows_processed: int
    rows_inserted: int


class PolicyStateImporter:
    def __init__(self, config: Config) -> None:
        self.config = config

    def ingest(
        self,
        *,
        file_path: Path,
        initiative_name: str,
        scope: str,
    ) -> PolicyStateImportResult:
        scope = scope.lower()
        states = load_policy_states(file_path)
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            initiative_fk = self._fetch_initiative(conn, initiative_name, scope)
            inserted = self._persist_states(conn, initiative_fk, states)
            conn.commit()
        return PolicyStateImportResult(rows_processed=len(states), rows_inserted=inserted)

    def _fetch_initiative(self, conn, name: str, scope: str) -> int:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM policy_initiatives WHERE initiative_id = %s AND scope = %s",
                (name, scope),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Initiative '{name}' with scope '{scope}' not found. Import definitions first.")
            return row[0]

    def _persist_states(self, conn, initiative_fk: int, states: list[PolicyStateEntry]) -> int:
        inserted = 0
        with conn.cursor() as cur:
            for state in states:
                control_ids = self._controls_for_policy(conn, initiative_fk, state.policy_definition_id)
                if not control_ids:
                    continue
                last_evaluated = _parse_timestamp(state.last_evaluated)
                for control_id in control_ids:
                    cur.execute(
                        """
                        DELETE FROM policy_states
                        WHERE initiative_fk = %s
                          AND control_id = %s
                          AND policy_definition_fk = %s
                          AND assignment_id = %s
                          AND resource_id = %s
                        """,
                        (
                            initiative_fk,
                            control_id,
                            state.policy_definition_id,
                            state.policy_assignment_id,
                            state.resource_id,
                        ),
                    )
                    cur.execute(
                        """
                        INSERT INTO policy_states (
                            initiative_fk,
                            control_id,
                            policy_definition_fk,
                            assignment_id,
                            resource_id,
                            compliance_state,
                            last_evaluated
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            initiative_fk,
                            control_id,
                            state.policy_definition_id,
                            state.policy_assignment_id,
                            state.resource_id,
                            state.compliance_state,
                            last_evaluated,
                        ),
                    )
                    inserted += 1
        return inserted

    def _controls_for_policy(self, conn, initiative_fk: int, policy_definition_id: str) -> list[str]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT control_id
                FROM policy_mappings
                WHERE initiative_fk = %s AND policy_definition_fk = %s
                """,
                (initiative_fk, policy_definition_id),
            )
            rows = cur.fetchall()
        return [row[0] for row in rows]


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.now(timezone.utc)
