"""Run helpers."""

from __future__ import annotations

from psycopg import Connection


def ensure_run(conn: Connection, *, project_id: int, run_id: str) -> int:
    """Ensure a runs row exists and return its primary key."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO runs (project_fk, run_id)
            VALUES (%s, %s)
            ON CONFLICT (project_fk, run_id) DO NOTHING
            RETURNING id
            """,
            (project_id, run_id),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "SELECT id FROM runs WHERE project_fk = %s AND run_id = %s",
            (project_id, run_id),
        )
        existing = cur.fetchone()
        if not existing:  # pragma: no cover
            raise RuntimeError(f"Failed to ensure run for project {project_id} run_id {run_id}")
        return existing[0]

