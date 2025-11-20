"""Control parameter database access."""

from __future__ import annotations

from psycopg import Connection

from ..config import Config
from ..store import get_connection
from .models import ControlParameter, normalize_parameter


class ControlService:
    def __init__(self, config: Config) -> None:
        self.config = config

    def list_parameters(self, control_id: str, project_id: int | None = None) -> list[ControlParameter]:
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            params = self._fetch_parameters(conn, control_id)
            if project_id is not None and params:
                value_map = self._fetch_parameter_values(conn, control_id, project_id)
                for param in params:
                    param.current_value = value_map.get(param.param_id)
        return params

    def ensure_parameter_exists(self, control_id: str, param_id: str) -> ControlParameter:
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            params = self._fetch_parameters(conn, control_id)
        for param in params:
            if param.param_id == param_id:
                return param
        raise ValueError(f"Parameter '{param_id}' not found on control '{control_id}'.")

    def _fetch_parameters(self, conn: Connection, control_id: str) -> list[ControlParameter]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT control_id, parameters_json
                FROM catalog_controls
                WHERE control_id = %s
                """,
                (control_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Control '{control_id}' not found in catalog. Import the catalog first.")
            _, params_json = row
        return [normalize_parameter(control_id, item) for item in params_json or []]

    def _fetch_parameter_values(self, conn: Connection, control_id: str, project_id: int) -> dict[str, str]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT param_id, value
                FROM parameter_values
                WHERE project_fk = %s AND control_id = %s
                """,
                (project_id, control_id),
            )
            rows = cur.fetchall()
        return {param_id: value for param_id, value in rows}

