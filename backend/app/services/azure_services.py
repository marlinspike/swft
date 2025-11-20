from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import os
import logging

logger = logging.getLogger("swft.backend.azure_services")


def _default_csv_path() -> Path:
    # backend/app/services -> /backend/app -> /backend -> /repo
    return Path(__file__).resolve().parents[3] / "lookup" / "azure_services.csv"


def _load_csv(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Azure services CSV not found at {path}")
    services: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            name = line.strip()
            if name:
                services.append(name)
    # Preserve order but deduplicate
    seen: set[str] = set()
    unique: list[str] = []
    for name in services:
        if name not in seen:
            unique.append(name)
            seen.add(name)
    return unique


@lru_cache
def get_azure_services() -> list[str]:
    """Return the curated list of Azure service names."""
    override = os.environ.get("SWFT_AZURE_SERVICES_FILE")
    path = Path(override) if override else _default_csv_path()
    try:
        return _load_csv(path)
    except Exception as exc:  # pragma: no cover - catastrophic configuration issue
        logger.error("Failed to load Azure services catalog from %s: %s", path, exc)
        return []


@lru_cache
def get_azure_service_lookup() -> dict[str, str]:
    """Lowercase lookup for canonical service names."""
    return {name.lower(): name for name in get_azure_services()}
