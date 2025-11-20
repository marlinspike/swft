"""Importer for OSCAL catalogs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from psycopg.types.json import Jsonb

from ...config import Config
from ...oscal.catalog import CatalogDocument, load_catalog
from ...store import get_connection
from ...store.files import pin_source_file
from ...store.versioning import ensure_version, VersionRecord
from ...utils.strings import slugify


@dataclass(slots=True)
class CatalogImportResult:
    version: VersionRecord
    control_count: int
    pinned_path: Path


class CatalogImporter:
    def __init__(self, config: Config) -> None:
        self.config = config

    def ingest(self, catalog_path: Path, *, name: str, pinned_name: str | None = None) -> CatalogImportResult:
        document = load_catalog(catalog_path)
        slug = slugify(pinned_name or document.metadata.title, default=name)
        dest_dir = self.config.paths.pinned / "catalogs"
        pinned_path, digest = pin_source_file(catalog_path, dest_dir, slug)
        version_label = document.metadata.version or document.metadata.oscal_version or name
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            version = ensure_version(
                conn,
                kind="catalog",
                name=name,
                version=version_label,
                content_hash=digest,
                source_uri=str(pinned_path),
            )
            with conn.cursor() as cur:
                for control in document.controls:
                    cur.execute(
                        """
                        INSERT INTO catalog_controls (
                            control_id,
                            family,
                            title,
                            parameters_json,
                            assessment_objectives_json,
                            catalog_version_ref
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (control_id) DO UPDATE
                        SET family=EXCLUDED.family,
                            title=EXCLUDED.title,
                            parameters_json=EXCLUDED.parameters_json,
                            assessment_objectives_json=EXCLUDED.assessment_objectives_json,
                            catalog_version_ref=EXCLUDED.catalog_version_ref
                        """,
                        (
                            control.control_id,
                            control.family,
                            control.title,
                            Jsonb(control.parameters),
                            Jsonb(control.assessment_objectives),
                            version.id,
                        ),
                    )
            conn.commit()
        return CatalogImportResult(
            version=version,
            control_count=len(document.controls),
            pinned_path=pinned_path,
        )

