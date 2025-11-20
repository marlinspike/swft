"""Ensure implemented-requirement placeholders exist."""

from __future__ import annotations

from psycopg import Connection


def ensure_implemented_requirement(
    conn: Connection,
    *,
    project_id: int,
    control_id: str,
    ownership: str = "Customer",
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO implemented_requirements (project_fk, control_id, ownership, status)
            VALUES (%s, %s, %s, 'Partial')
            ON CONFLICT (project_fk, control_id) DO NOTHING
            """,
            (project_id, control_id, ownership),
        )

