from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Final
import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_SBOM_CONTAINER: Final[str] = "sboms"
DEFAULT_SCAN_CONTAINER: Final[str] = "scans"
DEFAULT_RUN_CONTAINER: Final[str] = "runs"
DEFAULT_DELIMITER: Final[str] = "-"


@dataclass(frozen=True, slots=True)
class StorageSettings:
    account_name: str | None
    connection_string: str | None
    container_sboms: str
    container_scans: str
    container_runs: str
    delimiter: str
    local_blob_root: str | None


@dataclass(frozen=True, slots=True)
class AzureAuthSettings:
    tenant_id: str | None
    client_id: str | None
    client_secret: str | None


@dataclass(frozen=True, slots=True)
class AppSettings:
    storage: StorageSettings
    auth: AzureAuthSettings
    cache_ttl_seconds: int
    cache_max_items: int


def _env(name: str, default: str | None = None) -> str | None:
    """Retrieve an environment variable with an optional default fallback."""
    return os.getenv(name, default)


@lru_cache
def get_settings() -> AppSettings:
    """Load application configuration from environment variables (with .env support)."""
    storage = StorageSettings(
        account_name=_env("AZURE_STORAGE_ACCOUNT"),
        connection_string=_env("AZURE_STORAGE_CONNECTION_STRING"),
        container_sboms=_env("AZURE_STORAGE_CONTAINER_SBOMS", DEFAULT_SBOM_CONTAINER),
        container_scans=_env("AZURE_STORAGE_CONTAINER_SCANS", DEFAULT_SCAN_CONTAINER),
        container_runs=_env("AZURE_STORAGE_CONTAINER_RUNS", DEFAULT_RUN_CONTAINER),
        delimiter=_env("AZURE_STORAGE_BLOB_PREFIX_DELIMITER", DEFAULT_DELIMITER) or DEFAULT_DELIMITER,
        local_blob_root=_env("LOCAL_BLOB_ROOT")
    )
    auth = AzureAuthSettings(
        tenant_id=_env("AZURE_TENANT_ID"),
        client_id=_env("AZURE_CLIENT_ID"),
        client_secret=_env("AZURE_CLIENT_SECRET")
    )
    ttl = int(_env("CACHE_TTL_SECONDS", "60") or "60")
    max_items = int(_env("CACHE_MAX_ITEMS", "256") or "256")
    return AppSettings(storage=storage, auth=auth, cache_ttl_seconds=ttl, cache_max_items=max_items)
