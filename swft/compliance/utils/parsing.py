"""Input parsing helpers."""

from __future__ import annotations


def parse_csv_list(value: str | None) -> list[str]:
    if not value:
        return []
    parts = [segment.strip() for segment in value.split(",")]
    return [p for p in parts if p]


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"Cannot parse boolean value from '{value}'.")
