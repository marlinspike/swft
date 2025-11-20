from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import os
import logging

logger = logging.getLogger("swft.backend.azure_regions")


def _default_csv_path() -> Path:
    return Path(__file__).resolve().parents[3] / "lookup" / "azure_regions.csv"


def _load_csv(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Azure regions CSV not found at {path}")
    entries: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            name = line.strip()
            if name:
                entries.append(name)
    seen: set[str] = set()
    unique: list[str] = []
    for name in entries:
        if name not in seen:
            unique.append(name)
            seen.add(name)
    return unique


@lru_cache
def get_azure_regions() -> list[str]:
    override = os.environ.get("SWFT_AZURE_REGIONS_FILE")
    path = Path(override) if override else _default_csv_path()
    try:
        return _load_csv(path)
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to load Azure regions catalog from %s: %s", path, exc)
        return []


@lru_cache
def get_azure_region_lookup() -> dict[str, str]:
    return {name.lower(): name for name in get_azure_regions()}
