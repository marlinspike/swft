from __future__ import annotations

from pathlib import Path
from typing import Final

from .models import Facet
from ..core.cache import SimpleTTLCache, create_cache

SCHEMA_DIRECTORY: Final[Path] = Path(__file__).resolve().parent / "schema"

SCHEMA_FILE_MAP: Final[dict[str, Path]] = {
    "Run Manifest Schema": SCHEMA_DIRECTORY / "run_manifest.json",
    "SBOM Schema": SCHEMA_DIRECTORY / "sbom.json",
    "Trivy Scan Schema": SCHEMA_DIRECTORY / "trivy_scan.json",
    "General Context Schema": SCHEMA_DIRECTORY / "general.json",
}

FACET_SCHEMA_ORDER: Final[dict[Facet, list[str]]] = {
    Facet.run_manifest: ["Run Manifest Schema"],
    Facet.sbom: ["Run Manifest Schema", "SBOM Schema"],
    Facet.trivy: ["Run Manifest Schema", "Trivy Scan Schema"],
    Facet.general: ["Run Manifest Schema", "General Context Schema"],
}

_schema_cache: SimpleTTLCache = create_cache(max_items=16, ttl_seconds=300)


def _load_schema_text(label: str) -> str:
    """Read a schema file from disk with basic caching."""
    key = f"schema::{label}"
    if key in _schema_cache:
        return _schema_cache[key]
    path = SCHEMA_FILE_MAP[label]
    text = path.read_text(encoding="utf-8")
    _schema_cache[key] = text
    return text


def get_schema_bundle(facet: Facet) -> dict[str, str]:
    """Return an ordered mapping of schema label to raw JSON string for the chosen facet."""
    labels = FACET_SCHEMA_ORDER.get(facet, ["Run Manifest Schema"])
    bundle: dict[str, str] = {}
    for label in labels:
        if label not in SCHEMA_FILE_MAP:
            continue
        bundle[label] = _load_schema_text(label)
    return bundle
