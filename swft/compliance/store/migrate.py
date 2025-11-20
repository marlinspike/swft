"""
Simple SQL migration runner backed by psycopg.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from rich.console import Console

from ..config import Config
from .db import get_connection


MIGRATION_TABLE = "swft_schema_migrations"
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


@dataclass(slots=True)
class Migration:
    filename: str
    path: Path
    checksum: str


class MigrationRunner:
    def __init__(self, config: Config, console: Console | None = None) -> None:
        self.config = config
        self.console = console or Console()

    def apply(self) -> list[str]:
        """Apply all pending migrations."""
        migrations = list(self._discover())
        applied = []
        with get_connection(self.config) as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
                    id serial PRIMARY KEY,
                    filename TEXT NOT NULL UNIQUE,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            existing = {
                row[0]: row[1]
                for row in conn.execute(
                    f"SELECT filename, checksum FROM {MIGRATION_TABLE}"
                )
            }
            for migration in migrations:
                expected = existing.get(migration.filename)
                if expected:
                    if expected != migration.checksum:
                        raise RuntimeError(
                            f"Checksum mismatch for {migration.filename}: {expected} != {migration.checksum}"
                        )
                    continue
                self.console.print(f"[bold green]Applying[/] {migration.filename}")
                conn.execute(migration.path.read_text())
                conn.execute(
                    f"INSERT INTO {MIGRATION_TABLE}(filename, checksum) VALUES (%s, %s)",
                    (migration.filename, migration.checksum),
                )
                applied.append(migration.filename)
        return applied

    def status(self) -> tuple[Sequence[Migration], set[str]]:
        """Return (all migrations, applied filenames)."""
        migrations = list(self._discover())
        with get_connection(self.config) as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
                    id serial PRIMARY KEY,
                    filename TEXT NOT NULL UNIQUE,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            rows = conn.execute(f"SELECT filename FROM {MIGRATION_TABLE}")
            applied = {row[0] for row in rows}
        return migrations, applied

    def _discover(self) -> Iterable[Migration]:
        if not MIGRATIONS_DIR.exists():
            return []
        files = sorted(p for p in MIGRATIONS_DIR.iterdir() if p.suffix == ".sql")
        migrations: list[Migration] = []
        for path in files:
            data = path.read_bytes()
            checksum = hashlib.sha256(data).hexdigest()
            migrations.append(Migration(filename=path.name, path=path, checksum=checksum))
        return migrations

