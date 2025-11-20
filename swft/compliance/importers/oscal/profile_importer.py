"""Importer for OSCAL profiles (FedRAMP baselines)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...config import Config
from ...oscal.profile import load_profile
from ...store import get_connection
from ...store.files import pin_source_file
from ...store.versioning import ensure_version, VersionRecord
from ...utils.strings import slugify


@dataclass(slots=True)
class ProfileImportResult:
    version: VersionRecord
    control_count: int
    pinned_path: Path


class ProfileImporter:
    def __init__(self, config: Config) -> None:
        self.config = config

    def ingest(
        self,
        profile_path: Path,
        *,
        profile_name: str,
        pinned_name: str | None = None,
    ) -> ProfileImportResult:
        document = load_profile(profile_path)
        slug = slugify(pinned_name or profile_name, default=profile_name)
        dest_dir = self.config.paths.pinned / "baselines"
        pinned_path, digest = pin_source_file(profile_path, dest_dir, slug)
        version_label = document.metadata.version or document.metadata.oscal_version or profile_name
        with get_connection(self.config) as conn:
            conn.execute("SET search_path TO swft, public")
            version = ensure_version(
                conn,
                kind="baseline",
                name=profile_name,
                version=version_label,
                content_hash=digest,
                source_uri=str(pinned_path),
            )
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO baseline_profiles (profile_name, profile_version_ref)
                    VALUES (%s, %s)
                    ON CONFLICT (profile_name) DO UPDATE
                    SET profile_version_ref = excluded.profile_version_ref
                    RETURNING id
                    """,
                    (profile_name, version.id),
                )
                profile_id = cur.fetchone()[0]
                # Reset controls for this profile
                cur.execute("DELETE FROM baseline_controls WHERE profile_id = %s", (profile_id,))
                for control_id in document.control_ids:
                    cur.execute(
                        """
                        INSERT INTO baseline_controls (profile_id, control_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (profile_id, control_id),
                    )
            conn.commit()
        return ProfileImportResult(
            version=version,
            control_count=len(document.control_ids),
            pinned_path=pinned_path,
        )

