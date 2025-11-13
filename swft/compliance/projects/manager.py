"""Project persistence manager."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from psycopg import sql
from psycopg.errors import UniqueViolation

from ..config import Config
from ..store import get_connection


@dataclass(slots=True)
class ProjectRecord:
    id: int
    key: str
    services: list[str]
    regions: list[str]
    boundary_description: str | None


class ProjectsManager:
    def __init__(self, config: Config) -> None:
        self.config = config

    def create_project(
        self,
        *,
        key: str,
        services: list[str],
        regions: list[str],
        boundary_description: str | None,
    ) -> ProjectRecord:
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        INSERT INTO projects (project_key, boundary_description)
                        VALUES (%s, %s)
                        RETURNING id
                        """,
                        (key, boundary_description),
                    )
                except UniqueViolation as exc:  # pragma: no cover
                    raise ValueError(f"Project '{key}' already exists.") from exc
                project_id = cur.fetchone()[0]
                self._replace_collection(cur, "project_services", "service_name", project_id, services)
                self._replace_collection(cur, "project_regions", "region_name", project_id, regions)
            conn.commit()
        return ProjectRecord(
            id=project_id,
            key=key,
            services=services,
            regions=regions,
            boundary_description=boundary_description,
        )

    def upsert_project(
        self,
        *,
        key: str,
        services: list[str],
        regions: list[str],
        boundary_description: str | None,
    ) -> ProjectRecord:
        """Create or update a project, replacing services/regions/boundary in one transaction."""
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO projects (project_key, boundary_description)
                    VALUES (%s, %s)
                    ON CONFLICT (project_key)
                    DO UPDATE SET boundary_description = EXCLUDED.boundary_description
                    RETURNING id
                    """,
                    (key, boundary_description),
                )
                project_id = cur.fetchone()[0]
                self._replace_collection(cur, "project_services", "service_name", project_id, services)
                self._replace_collection(cur, "project_regions", "region_name", project_id, regions)
            conn.commit()
        return ProjectRecord(
            id=project_id,
            key=key,
            services=services,
            regions=regions,
            boundary_description=boundary_description,
        )

    def list_projects(self) -> list[ProjectRecord]:
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            with conn.cursor() as cur:
                cur.execute("SELECT id, project_key, boundary_description FROM projects ORDER BY project_key")
                rows = cur.fetchall()
                ids = [row[0] for row in rows]
                services_map = self._fetch_collection_map(cur, "project_services", "service_name", ids)
                regions_map = self._fetch_collection_map(cur, "project_regions", "region_name", ids)
        records: list[ProjectRecord] = []
        for project_id, key, boundary in rows:
            records.append(
                ProjectRecord(
                    id=project_id,
                    key=key,
                    services=services_map.get(project_id, []),
                    regions=regions_map.get(project_id, []),
                    boundary_description=boundary,
                )
            )
        return records

    def get_project(self, key: str) -> ProjectRecord:
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, project_key, boundary_description FROM projects WHERE project_key=%s",
                    (key,),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Project '{key}' not found.")
                project_id, project_key, boundary = row
                services_map = self._fetch_collection_map(cur, "project_services", "service_name", [project_id])
                regions_map = self._fetch_collection_map(cur, "project_regions", "region_name", [project_id])
        return ProjectRecord(
            id=project_id,
            key=project_key,
            services=services_map.get(project_id, []),
            regions=regions_map.get(project_id, []),
            boundary_description=boundary,
        )

    def _replace_collection(
        self,
        cur,
        table: str,
        column: str,
        project_id: int,
        values: Iterable[str],
    ) -> None:
        cur.execute(
            sql.SQL("DELETE FROM {} WHERE project_fk = %s").format(sql.Identifier(table)),
            (project_id,),
        )
        for value in values:
            cur.execute(
                sql.SQL("INSERT INTO {} (project_fk, {}) VALUES (%s, %s)").format(
                    sql.Identifier(table), sql.Identifier(column)
                ),
                (project_id, value),
            )

    def _fetch_collection_map(
        self,
        cur,
        table: str,
        column: str,
        project_ids: Iterable[int],
    ) -> dict[int, list[str]]:
        ids = list(project_ids)
        if not ids:
            return {}
        cur.execute(
            sql.SQL("SELECT project_fk, {} FROM {} WHERE project_fk = ANY(%s)").format(
                sql.Identifier(column),
                sql.Identifier(table),
            ),
            (ids,),
        )
        result: dict[int, list[str]] = {}
        for project_fk, value in cur.fetchall():
            result.setdefault(project_fk, []).append(value)
        return result
