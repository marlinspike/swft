"""Control metadata helpers."""

from __future__ import annotations

from .models import ControlParameter, normalize_parameter

try:  # pragma: no cover - optional import for environments without psycopg
    from .parameters import ControlService
except ModuleNotFoundError:  # pragma: no cover
    ControlService = None  # type: ignore
    __all__ = ["ControlParameter", "normalize_parameter"]
else:
    __all__ = ["ControlParameter", "ControlService", "normalize_parameter"]
