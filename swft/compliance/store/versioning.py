"""Helpers for version_registry interactions."""

from __future__ import annotations

from dataclasses import dataclass
from psycopg import Connection

SCHEMA = "swft"


@dataclass(slots=True)
class VersionRecord:
    id: int
    kind: str
    name: str
    version: str
    content_hash: str
    source_uri: str


def ensure_version(
    conn: Connection,
    *,
    kind: str,
    name: str,
    version: str,
    content_hash: str,
    source_uri: str,
) -> VersionRecord:
    """Insert or validate a version_registry row."""
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT id, content_hash, version, source_uri FROM {SCHEMA}.version_registry WHERE kind=%s AND name=%s",
            (kind, name),
        )
        row = cur.fetchone()
        if row:
            record_id, existing_hash, existing_version, existing_source = row
            if existing_hash != content_hash:
                raise ValueError(
                    f"Version '{name}' for kind '{kind}' already exists with hash {existing_hash}. "
                    "Use a new name or remove the existing record before re-importing."
                )
            # Optionally update source/version if changed
            if existing_version != version or existing_source != source_uri:
                cur.execute(
                    f"UPDATE {SCHEMA}.version_registry SET version=%s, source_uri=%s WHERE id=%s",
                    (version, source_uri, record_id),
                )
            return VersionRecord(
                id=record_id,
                kind=kind,
                name=name,
                version=existing_version,
                content_hash=existing_hash,
                source_uri=existing_source,
            )
        cur.execute(
            f"""
            INSERT INTO {SCHEMA}.version_registry (kind, name, source_uri, content_hash, version)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (kind, name, source_uri, content_hash, version),
        )
        new_id = cur.fetchone()[0]
        return VersionRecord(
            id=new_id,
            kind=kind,
            name=name,
            version=version,
            content_hash=content_hash,
            source_uri=source_uri,
        )

